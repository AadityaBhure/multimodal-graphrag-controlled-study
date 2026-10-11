from scripts.report_rq1_repair import summary,paired

def test_cluster_bootstrap_and_nulls():
    values={'q:a:normal':1.,'q:a:noisy':1.,'q:b:normal':1.,'q:b:noisy':None}
    result=summary(values)
    assert result['n']==3 and result['n_null']==1 and result['independent_query_families']==2
    assert result['mean']==1 and result['ci95']==[1.,1.]
    assert result==summary(values)
    assert summary({'q:a:normal':None})['mean'] is None

def test_exact_cluster_sign_test_does_not_count_stress_as_independent():
    a={f'q:{q}:{stress}':1. for q in range(3) for stress in ('normal','noisy')}
    b={q:0. for q in a}
    result=paired(a,b)
    assert result['mean']==1 and result['independent_query_families']==3
    assert result['p_cluster_sign_permutation']==.25
    assert paired(a,a)['p_cluster_sign_permutation']==1.
