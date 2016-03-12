# -*- coding: utf-8 -*-

from openerp.osv import osv


class AccountMoveLine(osv.osv):
    _inherit = "account.move.line"

    def _query_get(self, cr, uid, obj='l', context=None):
        query = super(AccountMoveLine, self)._query_get(
            cr, uid, obj=obj, context=context)
        if 'afr_analytics' in context or 'afr_analytic' in context:
            list_analytic_ids = context.get('afr_analytic') or \
                context.get('afr_analytics')
            ids2 = self.pool.get('account.analytic.account').search(
                cr, uid, [('parent_id', 'child_of', list_analytic_ids)],
                context=context)
            analytic_ids = ','.join([str(idx) for idx in ids2])

        if context.get('afr_analytic', False):
            query_analytic = obj + '.analytic_account_id IN (%s)' % (
                analytic_ids)
            query += 'AND ' + query_analytic
        elif context.get('afr_analytics', False):
            query_analytics = obj + '''
            .analytics_id IN (SELECT plan_id AS id
            FROM account_analytic_plan_instance_line
            WHERE analytic_account_id IN (%s))
            ''' % (analytic_ids)
            query += 'AND ' + query_analytics

        return query
