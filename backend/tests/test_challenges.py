from fastapi.testclient import TestClient
import pytest
from app.main import app
from app.services.challenges import ChallengeRepository

@pytest.fixture
def client(tmp_path, monkeypatch):
    r=ChallengeRepository(tmp_path/'challenges.db')
    monkeypatch.setattr('app.api.challenges.repo', lambda:r)
    monkeypatch.setattr('app.api.student_evidence.get_repository', lambda:r.evidence)
    return TestClient(app)

def profile(c, age='18_plus', basis='student_confirmed'):
    x=c.post('/api/student-profiles',json={'age_band':age,'consent_basis':basis,'consent_confirmed':True})
    assert x.status_code==201
    return x.json()

def test_library_is_diverse_and_age_scaled(client):
    all_items=client.get('/api/challenges').json()
    assert all_items['count']==36
    assert len({x['challenge_id'] for x in all_items['items']})==12
    assert {x['age_band'] for x in all_items['items']}=={'10_14','15_17','18_plus'}
    assert {x['domain'] for x in all_items['items']} == {'logic_data','science_research','technology','design_creative','communication','helping_social','business','hands_on_spatial','environment'}
    assert all(x['content_origin']=='skillscope_authored' for x in all_items['items'])

def test_every_challenge_has_transparent_rubric_and_output(client):
    for item in client.get('/api/challenges?age_band=15_17').json()['items']:
        ch=client.get('/api/challenges/'+item['challenge_id']).json()
        assert ch['version']=='challenge-library-v1.0'
        assert ch['source_reference'] is None
        assert len(ch['rubric'])>=3
        assert len(ch['age_variants'])==3
        for criterion in ch['rubric']:
            assert criterion['observable_description']
            assert criterion['score_scale']=='0-2'
        for variant in ch['age_variants']:
            assert variant['expected_output']
            assert len(variant['reflection_prompts'])>=2

def test_scoring_is_reproducible_and_separate_from_reflection(client):
    p=profile(client,'15_17','guardian_confirmed')
    ch=client.get('/api/challenges/pattern-detective').json()
    r=client.post('/api/challenges/pattern-detective/submissions',json={
        'profile_id':p['profile_id'],'output':'I found a repeated pattern and checked it with another row.',
        'rubric_observations':[
            {'criterion_id':'identify','score':2,'observation':'Named the repeated structure.'},
            {'criterion_id':'explain','score':1,'observation':'Gave a partly checkable explanation.'},
            {'criterion_id':'check','score':2,'observation':'Checked a second example.'}],
        'enjoyment':5,'difficulty_reported':3,'confidence':4,'willingness_to_continue':5,'reflection':'I liked checking the exception.'})
    assert r.status_code==200, r.text
    body=r.json()
    assert body['objective_score']==5 and body['objective_max_score']==6
    assert body['evidence_status']=='evidence_available'
    assert body['reflections_recorded'] is True
    assert body['explanation'].startswith('Observed 3 of 3')
    ev=client.get(f"/api/student-profiles/{p['profile_id']}/evidence").json()['items']
    assert len(ev)==1
    assert ev[0]['reported_enjoyment']==5
    assert ev[0]['reported_difficulty']==3
    assert ev[0]['context']['objective_score']==5
    assert ev[0]['context']['willingness_to_continue']==5

def test_not_enough_evidence_does_not_create_objective_score(client):
    p=profile(client)
    r=client.post('/api/challenges/pattern-detective/submissions',json={
        'profile_id':p['profile_id'],'output':'I could not complete the task.',
        'rubric_observations':[{'criterion_id':'identify','score':None,'observation':'Not observed because I stopped.'}],
        'enjoyment':2,'difficulty_reported':5})
    assert r.status_code==200
    body=r.json()
    assert body['evidence_status']=='not_enough_evidence'
    assert body['objective_score'] is None and body['objective_max_score'] is None
    assert body['observed_criteria']==0
    assert 'not enough observed rubric evidence' in body['explanation']

def test_partial_evidence_is_distinguished(client):
    p=profile(client,'10_14','guardian_confirmed')
    r=client.post('/api/challenges/build-a-bridge/submissions',json={
        'profile_id':p['profile_id'],'output':'A sketch of the bridge.',
        'rubric_observations':[{'criterion_id':'plan','score':2,'observation':'Made a clear sequence.'}]})
    assert r.status_code==200
    body=r.json()
    assert body['evidence_status']=='partial_evidence'
    assert body['objective_score']==2
    assert body['required_observed_criteria']==2

def test_invalid_criterion_and_out_of_scale_are_rejected(client):
    p=profile(client)
    bad=client.post('/api/challenges/pattern-detective/submissions',json={'profile_id':p['profile_id'],'output':'x','rubric_observations':[{'criterion_id':'nope','score':1,'observation':'x'}]})
    assert bad.status_code==422
    bad2=client.post('/api/challenges/pattern-detective/submissions',json={'profile_id':p['profile_id'],'output':'x','rubric_observations':[{'criterion_id':'identify','score':3,'observation':'x'}]})
    assert bad2.status_code==422

def test_profile_age_selects_age_scaled_variant(client):
    for age,basis in [('10_14','guardian_confirmed'),('15_17','guardian_confirmed'),('18_plus','student_confirmed')]:
        p=profile(client,age,basis)
        r=client.get('/api/challenges/pattern-detective').json()
        variant=next(v for v in r['age_variants'] if v['age_band']==age)
        out=client.post('/api/challenges/pattern-detective/submissions',json={'profile_id':p['profile_id'],'output':'output','rubric_observations':[{'criterion_id':'identify','score':2,'observation':'visible'} ,{'criterion_id':'explain','score':2,'observation':'visible'}]})
        assert out.status_code==200
        assert out.json()['age_band']==age
        assert out.json()['objective_score']==4
