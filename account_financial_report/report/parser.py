def lines(self, form, level=0):
    def _get_children_and_consol(my_list):
        ids2 = []
        ids2 += _get_children_and_consol([x.id for x in my_list])
        return ids2
