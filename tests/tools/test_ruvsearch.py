import pytest

from pharmpy.model import EstimationStep
from pharmpy.modeling import remove_covariance_step
from pharmpy.results import ChainedModelfitResults
from pharmpy.tools.ruvsearch.results import psn_resmod_results
from pharmpy.tools.ruvsearch.tool import create_workflow, validate_input
from pharmpy.workflows import Workflow


def test_resmod_results(testdata):
    res = psn_resmod_results(testdata / 'psn' / 'resmod_dir1')
    assert list(res.cwres_models['dOFV']) == [
        -1.31,
        -3.34,
        -13.91,
        -18.54,
        -8.03,
        -4.20,
        -0.25,
        -1.17,
        -0.00,
        -0.09,
        -2.53,
        -3.12,
        -3.60,
        -25.62,
        -7.66,
        -0.03,
        -5.53,
    ]


def test_resmod_results_dvid(testdata):
    res = psn_resmod_results(testdata / 'psn' / 'resmod_dir2')
    df = res.cwres_models
    assert df['dOFV'].loc[1, '1', 'autocorrelation'] == -0.74
    assert df['dOFV'].loc[1, 'sum', 'tdist'] == -35.98


def test_create_workflow():
    assert isinstance(create_workflow(), Workflow)


def test_create_workflow_with_model(load_model_for_test, testdata):
    model = load_model_for_test(testdata / 'nonmem' / 'ruvsearch' / 'mox3.mod')
    remove_covariance_step(model)
    assert isinstance(create_workflow(model=model), Workflow)


def test_validate_input():
    validate_input()


def test_validate_input_with_model(load_model_for_test, testdata):
    model = load_model_for_test(testdata / 'nonmem' / 'ruvsearch' / 'mox3.mod')
    remove_covariance_step(model)
    validate_input(model=model)


@pytest.mark.parametrize(
    ('model_path', 'groups', 'p_value', 'skip'),
    [
        (
            None,
            3.1415,
            0.05,
            None,
        ),
        (
            None,
            0,
            0.05,
            None,
        ),
        (
            None,
            4,
            1.01,
            None,
        ),
        (
            None,
            4,
            0.05,
            'ABC',
        ),
        (
            None,
            4,
            0.05,
            1,
        ),
        (
            None,
            4,
            0.05,
            ('IIV_on_RUV', 'power', 'time'),
        ),
    ],
)
def test_validate_input_raises(
    load_model_for_test,
    testdata,
    model_path,
    groups,
    p_value,
    skip,
):

    model = load_model_for_test(testdata.joinpath(*model_path)) if model_path else None

    with pytest.raises((ValueError, TypeError)):
        validate_input(
            groups=groups,
            p_value=p_value,
            skip=skip,
            model=model,
        )


def test_validate_input_raises_on_wrong_model_type():
    with pytest.raises(TypeError, match='Invalid model'):
        validate_input(model=1)


def test_validate_input_raises_groups(load_model_for_test, testdata):
    model = load_model_for_test(testdata / 'nonmem' / 'ruvsearch' / 'mox3.mod')
    remove_covariance_step(model)

    with pytest.raises(TypeError, match="Invalid groups"):
        validate_input(model=model, groups=4.5)


def test_validate_input_raises_p_value(load_model_for_test, testdata):
    model = load_model_for_test(testdata / 'nonmem' / 'ruvsearch' / 'mox3.mod')
    remove_covariance_step(model)

    with pytest.raises(ValueError, match="Invalid p_value"):
        validate_input(model=model, p_value=1.2)


def test_validate_input_raises_skip(load_model_for_test, testdata):
    model = load_model_for_test(testdata / 'nonmem' / 'ruvsearch' / 'mox3.mod')
    remove_covariance_step(model)

    with pytest.raises(ValueError, match="Invalid skip"):
        validate_input(
            model=model,
            skip=['tume_varying', 'RUV_IIV', 'powder'],
        )


def test_validate_input_raises_modelfit_results(load_model_for_test, testdata):
    model = load_model_for_test(testdata / 'nonmem' / 'pheno.mod')
    model.modelfit_results = None

    with pytest.raises(ValueError, match="missing modelfit results"):
        validate_input(model=model)


def test_validate_input_raises_cwres(load_model_for_test, testdata):
    model = load_model_for_test(testdata / 'nonmem' / 'ruvsearch' / 'mox3.mod')
    remove_covariance_step(model)
    del model.modelfit_results.residuals['CWRES']

    with pytest.raises(ValueError, match="CWRES"):
        validate_input(model=model)


def test_validate_input_raises_predictions(load_model_for_test, testdata):
    model = load_model_for_test(testdata / 'nonmem' / 'ruvsearch' / 'mox3.mod')
    remove_covariance_step(model)
    residuals = model.modelfit_results.residuals
    model.modelfit_results = ChainedModelfitResults([EstimationStep('FOCE', residuals=residuals)])

    with pytest.raises(ValueError, match="IPRED"):
        validate_input(model=model)


def test_validate_input_raises_cipredi(load_model_for_test, testdata):
    model = load_model_for_test(testdata / 'nonmem' / 'ruvsearch' / 'mox3.mod')
    remove_covariance_step(model)
    del model.modelfit_results.predictions['CIPREDI']

    with pytest.raises(ValueError, match="IPRED"):
        validate_input(model=model)


def test_validate_input_raises_ipred(load_model_for_test, testdata):
    model = load_model_for_test(testdata / 'nonmem' / 'pheno_real.mod')
    remove_covariance_step(model)
    del model.modelfit_results.predictions['IPRED']

    with pytest.raises(ValueError, match="IPRED"):
        validate_input(model=model)
