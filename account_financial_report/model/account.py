# -*- coding: utf-8 -*-

from openerp.osv import osv


class AccountMoveLine(osv.osv):
    _inherit = "account.move.line"

    def _query_get(self, cr, uid, obj='l', context=None):
        query = super(AccountMoveLine, self)._query_get(
            cr, uid, obj=obj, context=context)
        if context.get('afr_analytic', False):
            list_analytic_ids = context.get('afr_analytic')
            ids2 = self.pool.get('account.analytic.account').search(
                cr, uid, [('parent_id', 'child_of', list_analytic_ids)],
                context=context)
            query += 'AND ' + obj + '.analytic_account_id in (%s)' % (
                ','.join([str(idx) for idx in ids2]))

        return query
