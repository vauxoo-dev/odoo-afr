def recursive_method(my_list, ids):
    ids2 = []
    if not ids2:
        ids2 += recursive_method([x.id for x in my_list])
    return ids2
