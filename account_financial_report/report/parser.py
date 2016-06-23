class AccountBalance(report_sxw.rml_parse):
    _name = 'afr.parser'

    def _get_partner_balance(self, account, init_period, ctx=None):
        res = []
        ctx = ctx or {}
        if account['type'] in ('other', 'liquidity', 'receivable', 'payable'):
            sql_query = """
                SELECT
                    CASE
                        WHEN aml.partner_id IS NOT NULL
                        THEN (SELECT name FROM res_partner
                                WHERE aml.partner_id = id)
                    ELSE 'UNKNOWN'
                        END AS partner_name,
                    CASE
                        WHEN aml.partner_id IS NOT NULL
                       THEN aml.partner_id
                    ELSE 0
                        END AS p_idx,
                    %s,
                    %s,
                    %s,
                    %s
                FROM account_move_line AS aml
                INNER JOIN account_account aa ON aa.id = aml.account_id
                INNER JOIN account_move am ON am.id = aml.move_id
                %s
                GROUP BY p_idx, partner_name
                """

            where_posted = ''
            if ctx.get('state', 'posted') == 'posted':
                where_posted = "AND am.state = 'posted'"

            cur_periods = ', '.join([str(i) for i in ctx['periods']])
            init_periods = ', '.join([str(i) for i in init_period])

            where = """
                WHERE aml.period_id IN (%s)
                    AND aa.id = %s
                    AND aml.state <> 'draft'
                    """ % (init_periods, account['id'])
            query_init = sql_query % ('SUM(aml.debit) AS init_dr',
                                      'SUM(aml.credit) AS init_cr',
                                      '0.0 AS bal_dr',
                                      '0.0 AS bal_cr',
                                      where + where_posted)

            where = """
                WHERE aml.period_id IN (%s)
                    AND aa.id = %s
                    AND aml.state <> 'draft'
                    """ % (cur_periods, account['id'])

            query_bal = sql_query % ('0.0 AS init_dr',
                                     '0.0 AS init_cr',
                                     'SUM(aml.debit) AS bal_dr',
                                     'SUM(aml.credit) AS bal_cr',
                                     where + where_posted)

            query = '''
                SELECT
                    partner_name,
                    p_idx,
                    SUM(init_dr)-SUM(init_cr) AS balanceinit,
                    SUM(bal_dr) AS debit,
                    SUM(bal_cr) AS credit,
                    SUM(init_dr) - SUM(init_cr) + SUM(bal_dr) - SUM(bal_cr)
                        AS balance
                FROM (
                    SELECT
                    *
                    FROM (%s) vinit
                    UNION ALL (%s)
                ) v
                GROUP BY p_idx, partner_name
                ORDER BY partner_name
                ''' % (query_init, query_bal)

            self.cr.execute(query)
            res_dict = self.cr.dictfetchall()
            unknown = False
            for det in res_dict:
                inicial, debit, credit, balance = det['balanceinit'], det[
                    'debit'], det['credit'], det['balance'],
                data = {
                    'partner_name': det['partner_name'],
                    'balanceinit': inicial,
                    'debit': debit,
                    'credit': credit,
                    'balance': balance,
                }
                if not det['p_idx']:
                    unknown = data
                    continue
                res.append(data)
            if unknown:
                res.append(unknown)
        return res

    def _get_analytic_ledger(self, account, ctx=None):
        """
        TODO
        """
        ctx = ctx or {}
        res = []
        aml_obj = self.pool.get('account.move.line')
        if account['type'] in ('other', 'liquidity', 'receivable', 'payable'):
            # TODO: When period is empty fill it with all periods from
            # fiscalyear but the especial period
            periods = ', '.join([str(i) for i in ctx['periods']])
            where = """where aml.period_id in (%s) and aa.id = %s
            and aml.state <> 'draft'""" % (periods, account['id'])
            if ctx.get('state', 'posted') == 'posted':
                where += "AND am.state = 'posted'"
            sql_detalle = """select aml.id as id, aj.name as diario,
                aa.name as descripcion,
                (select name from res_partner where aml.partner_id = id)
                as partner,
                aa.code as cuenta, aa.id as aa_id, aml.name as name,
                aml.ref as ref,
                (select name from res_currency where aml.currency_id = id)
                as currency,
                aml.currency_id as currency_id,
                aml.partner_id as partner_id,
                aml.amount_currency as amount_currency,
                case when aml.debit is null then 0.00 else aml.debit end
                as debit,
                case when aml.credit is null then 0.00 else aml.credit end
                as credit,
                (select code from account_analytic_account
                where  aml.analytic_account_id = id) as analitica,
                aml.date as date, ap.name as periodo,
                am.name as asiento
                from account_move_line aml
                inner join account_journal aj on aj.id = aml.journal_id
                inner join account_account aa on aa.id = aml.account_id
                inner join account_period ap on ap.id = aml.period_id
                inner join account_move am on am.id = aml.move_id """ \
                + where + """ order by date, am.name"""

            self.cr.execute(sql_detalle)
            resultat = self.cr.dictfetchall()
            balance = account['balanceinit']
            company_currency = self.pool.get('res.currency').browse(
                self.cr, self.uid,
                self.get_company_currency(ctx['company_id'])).name
            for det in resultat:
                balance += det['debit'] - det['credit']
                res.append({
                    'aa_id': det['aa_id'],
                    'cuenta': det['cuenta'],
                    'id': det['id'],
                    'aml_brw': aml_obj.browse(self.cr, self.uid, det['id'],
                                              context=ctx),
                    'date': det['date'],
                    'journal': det['diario'],
                    'partner_id': det['partner_id'],
                    'partner': det['partner'],
                    'name': det['name'],
                    'entry': det['asiento'],
                    'ref': det['ref'],
                    'debit': det['debit'],
                    'credit': det['credit'],
                    'analytic': det['analitica'],
                    'period': det['periodo'],
                    'balance': balance,
                    'currency': det['currency'] or company_currency,
                    'currency_id': det['currency_id'],
                    'amount_currency': det['amount_currency'],
                    'amount_company_currency': det['debit'] - det['credit'] if
                    det['currency'] is None else 0.0,
                    'differential': det['debit'] - det['credit']
                    if det['currency'] is not None and not
                    det['amount_currency'] else 0.0,
                })
        return res

    def _get_journal_ledger(self, account, ctx=None):
        res = []
        am_obj = self.pool.get('account.move')
        if account['type'] in ('other', 'liquidity', 'receivable', 'payable'):
            # TODO: When period is empty fill it with all periods from
            # fiscalyear but the especial period
            periods = ', '.join([str(i) for i in ctx['periods']])
            where = \
                """where aml.period_id in (%s) and aa.id = %s
                    and aml.state <> 'draft'""" % (periods, account['id'])
            if ctx.get('state', 'posted') == 'posted':
                where += "AND am.state = 'posted'"
            sql_detalle = """SELECT
                DISTINCT am.id as am_id,
                aj.name as diario,
                am.name as name,
                am.date as date,
                ap.name as periodo
                from account_move_line aml
                inner join account_journal aj on aj.id = aml.journal_id
                inner join account_account aa on aa.id = aml.account_id
                inner join account_period ap on ap.id = aml.period_id
                inner join account_move am on am.id = aml.move_id """ \
                    + where + """ order by date, am.name"""

            self.cr.execute(sql_detalle)
            resultat = self.cr.dictfetchall()
            for det in resultat:
                res.append({
                    'am_id': det['am_id'],
                    'journal': det['diario'],
                    'name': det['name'],
                    'date': det['date'],
                    'period': det['periodo'],
                    'obj': am_obj.browse(self.cr, self.uid, det['am_id'])
                })
        return res

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

