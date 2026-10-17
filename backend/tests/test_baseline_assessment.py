from fastapi.testclient import TestClient
import pytest
from app.main import app
from app.services.baseline_assessment import BaselineAssessmentRepository

@pytest.fixture
def client(tmp_path, monkeypatch):
    r=BaselineAssessmentRepository(tmp_path/'baseline.db')
    monkeypatch.setattr('app.api.baseline_assessment.repo', lambda:r)
    monkeypatch.setattr('app.api.student_evidence.get_repository', lambda:r.evidence)
    return TestClient(app)

def profile(c, age='18_plus', basis='student_confirmed'):
    x=c.post('/api/student-profiles',json={'age_band':age,'consent_basis':basis,'consent_confirmed':True})
    assert x.status_code==201
    return x.json()

def test_age_bands_receive_different_modes(client):
    a=profile(client,'10_14','guardian_confirmed'); b=profile(client,'15_17','guardian_confirmed'); d=profile(client)
    aa=client.post(f"/api/baseline-assessments/for/{a['profile_id']}").json(); bb=client.post(f"/api/baseline-assessments/for/{b['profile_id']}").json(); dd=client.post(f"/api/baseline-assessments/for/{d['profile_id']}").json()
    assert aa['mode']=='discover_and_shape'; assert bb['mode']=='explore_and_validate'; assert dd['mode']=='develop_and_optimize'
    assert aa['notice'].startswith('This is an initial snapshot')
    assert len(aa['items'])==9 and len(dd['items'])==9
    assert aa['items'][0]['prompt'] != dd['items'][0]['prompt']
    assert any(item['item_type']=='mini_activity' for item in aa['items'])

def test_baseline_allows_skip_and_unknown_is_not_zero(client):
    p=profile(client); a=client.post(f"/api/baseline-assessments/for/{p['profile_id']}").json()
    out=client.post('/api/baseline-assessments/submit',json={'assessment_id':a['assessment_id'],'responses':[{'item_id':a['items'][0]['item_id'],'skipped':True}]})
    assert out.status_code==200
    result=out.json(); first=result['domain_results'][0]
    assert first['evidence_status']=='unknown'; assert first['skipped_count']==1; assert result['evidence_created_count']==0

def test_submission_creates_contextual_evidence_not_aptitude_score(client):
    p=profile(client); a=client.post(f"/api/baseline-assessments/for/{p['profile_id']}").json()
    responses=[{'item_id':a['items'][0]['item_id'],'answer':'Quite a lot','confidence':4},{'item_id':a['items'][1]['item_id'],'answer':'I would test two explanations','confidence':3}]
    out=client.post('/api/baseline-assessments/submit',json={'assessment_id':a['assessment_id'],'responses':responses})
    assert out.status_code==200; body=out.json(); assert body['evidence_created_count']==2
    ev=client.get(f"/api/student-profiles/{p['profile_id']}/evidence").json()['items']
    assert len(ev)==2
    assert all('score' not in e for e in body['domain_results'])
    assert all(e['context']['baseline_version']=='baseline-exploratory-v1.0' for e in ev)
    assert any(e['evidence_type']=='challenge_performance' for e in ev)

def test_duplicate_item_and_unknown_item_rejected(client):
    p=profile(client); a=client.post(f"/api/baseline-assessments/for/{p['profile_id']}").json(); item=a['items'][0]['item_id']
    dup=client.post('/api/baseline-assessments/submit',json={'assessment_id':a['assessment_id'],'responses':[{'item_id':item,'answer':'A'},{'item_id':item,'answer':'B'}]})
    assert dup.status_code==422
    bad=client.post('/api/baseline-assessments/submit',json={'assessment_id':a['assessment_id'],'responses':[{'item_id':'nope','answer':'A'}]})
    assert bad.status_code==422

def test_assessment_cannot_be_submitted_twice(client):
    p=profile(client); a=client.post(f"/api/baseline-assessments/for/{p['profile_id']}").json(); body={'assessment_id':a['assessment_id'],'responses':[{'item_id':a['items'][0]['item_id'],'answer':'A'}]}
    assert client.post('/api/baseline-assessments/submit',json=body).status_code==200
    assert client.post('/api/baseline-assessments/submit',json=body).status_code==422
