def lines(self, form, level=0):
    def _get_children_and_consol():
            ids2 = []
            ids2 += _get_children_and_consol(
                        cr, uid, [x.id for x in aa_brw.child_id], level,
                        context, change_sign=change_sign)
            return ids2


