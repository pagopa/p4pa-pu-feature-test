from datetime import datetime

from behave import then

from api.classifications import get_classification


@then("the classification labels are {labels}")
def step_check_classification(context, labels: str):
    date_now = datetime.now().strftime('%Y-%m-%d')

    labels = labels.split(sep=', ')

    res = get_classification(token=context.token, organization_id=context.org_info.id,
                             last_classification_date_from=date_now, last_classification_date_to=date_now,
                             iuv=context.installment_paid.iuv)

    assert res.status_code == 200
    assert len(res.json()['content']) != 0

    classification_labels = list(cl['label'] for cl in res.json()['content'])

    assert len(labels) == len(classification_labels)
    assert any(label in classification_labels for label in labels)
