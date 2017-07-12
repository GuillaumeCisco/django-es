import logging
from elasticsearch.exceptions import NotFoundError
from django_es import es_instance
from .mappings import mapping

from elasticsearch.helpers import bulk


def update_index(model_items, model, action='index', bulk_size=100, num_docs=-1, refresh=True):
    """
    Updates the index for the provided model_items.
    :param model_items: a list of model_items (django Model instances, or proxy instances) which are to be
    indexed/updated or deleted.
    If action is 'index', the model_items must be serializable objects. If action is 'delete', the model_items must be
    primary keys corresponding to objects in the index.
    :param model: Model that will get the index index instance related (i.e indice).
    :param action: the action that you'd like to perform on this group of data. Must be in ('index', 'delete') and
    defaults to 'index.'
    :param bulk_size: bulk size for indexing. Defaults to 100.
    :param num_docs: maximum number of model_items from the provided list to be indexed.
    :param refresh: a boolean that determines whether to refresh the index, making all operations performed since the
    last refresh
    immediately available for search, instead of needing to wait for the scheduled Elasticsearch execution. Defaults to
    True.

    :note: If model_items contain multiple models, then num_docs is applied to *each* model. For example, if bulk_size
    is set to 5, and item contains models Article and Article2, then 5 model_items of Article *and* 5 model_items of
    Article2 will be indexed.
    """
    if action == 'delete' and not hasattr(model_items, '__iter__'):
        raise ValueError("If action is 'delete', model_items must be an iterable of primary keys.")

    logging.info('Getting index for model {}.'.format(model.__name__))

    index_instance = mapping.get_index_instance(model)

    # if the last indexes not equal to the populated index, recreate index, before change
    index_name = index_instance.populate_index()
    if index_name not in index_instance.indexes:
        mapping.register(model, index_instance.__class__, index_name)

    if num_docs == -1:
        if isinstance(model_items, (list, tuple)):
            num_docs = len(model_items)
        else:  # can be a query
            num_docs = model_items.count()
    else:
        logging.warning('Limiting the number of model_items to {} to {}.'.format(action, num_docs))

    logging.info('{} {} documents on index {}'.format(action, num_docs, index_name))
    prev_step = 0
    max_docs = num_docs + bulk_size if num_docs > bulk_size else bulk_size + 1
    for next_step in range(bulk_size, max_docs, bulk_size):
        logging.info('{}: documents {} to {} of {} total on index {}.'.format(action.capitalize(), prev_step, next_step,
                                                                              num_docs, index_name))
        data = create_indexed_document(index_instance, model_items[prev_step:next_step], action)
        bulk(es_instance, data, index=index_name, doc_type=index_instance.doc_type, raise_on_error=True)
        prev_step = next_step

    if refresh:
        es_instance.indices.refresh(index=index_name)


def delete_index_item(item, model, refresh=True):
    """
    Deletes an item from the index.
    :param item: must be a serializable object.
    :param model: Model that will get the index index instance related (indice).
    :param refresh: a boolean that determines whether to refresh the index, making all operations performed since the
    last refresh immediately available for search, instead of needing to wait for the scheduled Elasticsearch execution.
    Defaults to True.
    """

    logging.info('Getting index for model {}.'.format(model.__name__))

    index_instance = mapping.get_index_instance(model)
    # if the last indexes not equal to the populated index, recreate index, before change
    index_name = index_instance.populate_index()
    if index_name not in index_instance.indexes:
        mapping.register(model, index_instance.__class__, index_name)

    item_es_id = getattr(item, index_instance.id_field)
    try:
        es_instance.delete(index_name, index_instance.doc_type, item_es_id)
    except NotFoundError as e:
        logging.warning(
            'NotFoundError: could not delete {}.{} from index {}: {}.'.format(model.__name__, item_es_id, index_name,
                                                                              str(e)))

    if refresh:
        es_instance.indices.refresh(index=index_name)


def create_indexed_document(index_instance, model_items, action):
    """
    Creates the document that will be passed into the bulk index function.
    Either a list of serialized objects to index, or a a dictionary specifying the primary keys of items to be delete.
    """
    data = []
    if action == 'delete':
        for pk in model_items:
            data.append({'_id': str(pk), '_op_type': action})
    else:
        for doc in model_items:
            if index_instance.matches_indexing_condition(doc):
                d = index_instance.serialize_object(doc)
                pk = getattr(doc, index_instance.id_field)
                # if working with post save signal, we know the correct pk field
                if pk is not None:
                    d['_id'] = str(pk)
                data.append(d)
    return data
