class AccountBalance(report_sxw.rml_parse):
    _name = 'afr.parser'

    def lines(self, form, level=0):
        """
        Returns all the data needed for the report lines (account info plus
        debit/credit/balance in the selected period and the full year)
        """
        account_obj = self.pool.get('account.account')
        period_obj = self.pool.get('account.period')
        fiscalyear_obj = self.pool.get('account.fiscalyear')

        def _get_children_and_consol(cr, uid, ids, level, context=None,
                                     change_sign=False):
            aa_obj = self.pool.get('account.account')
            ids2 = []
            for aa_brw in aa_obj.browse(cr, uid, ids, context):
                if aa_brw.child_id and aa_brw.level < \
                        level and aa_brw.type != 'consolidation':
                    if not change_sign:
                        ids2.append([aa_brw.id, True, False, aa_brw])
                    ids2 += _get_children_and_consol(
                        cr, uid, [x.id for x in aa_brw.child_id], level,
                        context, change_sign=change_sign)
                    if change_sign:
                        ids2.append(aa_brw.id)
                    else:
                        ids2.append([aa_brw.id, False, True, aa_brw])
                else:
                    if change_sign:
                        ids2.append(aa_brw.id)
                    else:
                        ids2.append([aa_brw.id, True, True, aa_brw])
            return ids2

        #######################################################################
        # CONTEXT FOR ENDIND BALANCE                                          #
        #######################################################################
        def _ctx_end(ctx):
            ctx_end = ctx
            ctx_end['filter'] = form.get('filter', 'all')
            ctx_end['fiscalyear'] = fiscalyear.id

            if form['filter'] in ['byperiod', 'all']:
                ctx_end['periods'] = period_obj.search(
                    self.cr, self.uid,
                    [('id', 'in', form['periods'] or
                      ctx_end.get('periods', False)),
                     ('special', '=', False)])

            return ctx_end.copy()

        #######################################################################
        # CONTEXT FOR INITIAL BALANCE                                         #
        #######################################################################

        def _ctx_init(ctx):
            ctx_init = self.context.copy()
            ctx_init['filter'] = form.get('filter', 'all')
            ctx_init['fiscalyear'] = fiscalyear.id

            if form['filter'] in ['byperiod', 'all']:
                ctx_init['periods'] = form['periods']
                date_start = min(
                    [period.date_start for period in
                     period_obj.browse(self.cr, self.uid,
                                       ctx_init['periods'])])
                ctx_init['periods'] = period_obj.search(
                    self.cr, self.uid, [('fiscalyear_id', '=', fiscalyear.id),
                                        ('date_stop', '<=', date_start)])

            return ctx_init.copy()

