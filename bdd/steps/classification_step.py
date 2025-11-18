from datetime import datetime

from behave import then

from api.classifications import get_classification


@then("the classification labels are {labels}")
@then("the classification labels for each transfer are {labels}")
def step_check_classification(context, labels: str):
    date_now = datetime.now().strftime('%Y-%m-%d')
    installment_paid = context.installment_paid

    labels = labels.split(sep=', ')

    res = get_classification(token=context.token, organization_id=context.org_info.id,
                             last_classification_date_from=date_now, last_classification_date_to=date_now,
                             iuv=installment_paid.iuv)

    assert res.status_code == 200
    assert len(res.json()['content']) != 0
    classifications = res.json()['content']

    classification_transfer_map = {}
    for classification in classifications:
        classification_transfer_map.setdefault(classification['transferIndex'], []).append(classification)

    for transfer in installment_paid.transfers:
        classification_labels = list(cl['label'] for cl in classification_transfer_map[transfer.transfer_index])
        assert len(labels) == len(classification_labels)
        assert any(label in classification_labels for label in labels)
