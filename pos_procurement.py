# -*- coding: utf-8 -*-
from datetime import datetime, timedelta

from openerp import models, fields, api
from openerp.tools import DEFAULT_SERVER_DATETIME_FORMAT
import logging

_logger = logging.getLogger(__name__)


class PosConfig(models.Model):
    _inherit = 'pos.config'
    
    def _default_warehouse(self):
        res = self.env['stock.warehouse'].search([('company_id', '=', self.env.user.company_id.id)], limit=1)
        if res:
            return res
        return self.env['stock.warehouse']
    
    force_availability = fields.Boolean(string='Force availability', default=True)
    warehouse_id = fields.Many2one('stock.warehouse', string='Warehouse', default=_default_warehouse, required=True)
    proc_rule = fields.Many2one('procurement.rule', string='Procurement rule', required=False)

class PosOrder(models.Model):
    _inherit = 'pos.order'
    
    delivery_count = fields.Integer(string='Delivery Orders', compute='_compute_delivery_count')

    @api.multi
    @api.depends('picking_id')
    def _compute_delivery_count(self):
        for order in self:
            order.delivery_count = len(order.picking_id)
    
    @api.multi
    def create_picking(self):
        self.create_procurement_order()

    @api.multi
    def create_procurement_order(self):
        proc_obj = self.env['procurement.order']
        proc_group_obj = self.env['procurement.group']
        picking_obj = self.env['stock.picking']
        
        for order in self:
            proc_group = None
            rule = order.session_id.config_id.proc_rule
            for line in order.lines:
                if line.qty <= 0: #TODO deal with qty negative case
                    continue
                
                if not proc_group:
                    proc_group = proc_group_obj.create({
                        'name': order.name,
                        'move_type': 'one',
                        'partner_id': order.partner_id.id,
                    })
                
                #this can not be done correctly like this, because it depends on whether the client is taking the shit now,
                #or will pick it up at a certain date. Modify the javascript/html/css of the PoS to do this correctly.
                date_planned = datetime.strptime(order.date_order, DEFAULT_SERVER_DATETIME_FORMAT)\
                    + timedelta(days=line.product_id.sale_delay or 0.0) - timedelta(days=line.company_id.security_lead)
                
                if order.partner_id:
                    destination_id = order.partner_id.property_stock_customer.id
                else:
                    customerloc, supplierloc = self.pool['stock.warehouse']._get_partner_locations(self.env.cr, self.env.uid, [], context=self.env.context)
                    destination_id = customerloc.id
                
                vals = {
                    'name': line.product_id.name,
                    'origin': order.name,
                    'product_id': line.product_id.id,
                    'product_qty': abs(line.qty),
                    'product_uom': line.product_id.uom_id.id,
                    'company_id': line.company_id.id,
                    'group_id': proc_group.id,
                    'pos_line_id': line.id,
                    'date_planned': date_planned.strftime(DEFAULT_SERVER_DATETIME_FORMAT),
                    'partner_dest_id': order.partner_id.id,
                    'warehouse_id': order.session_id.config_id.warehouse_id.id,
                    'location_id': destination_id,
                }
                if rule:
                    vals.update({'rule_id':rule.id})
                proc_obj.create(vals)
            
            if not proc_group:
                continue
            
            pickings = picking_obj.search([('group_id', '=', proc_group.id)])
            if not pickings:
                _logger.debug("Did not have picking_id, check procurement exceptions")
                continue
            
            pick = pickings[0]  #the PoS should always create a single picking, if not we need to change the pos_order table
            order.picking_id = pick
            if order.session_id.config_id.force_availability:
                pick.force_assign()
                # Mark pack operations as done
                for pack in pick.pack_operation_ids:
                    pack.write({'qty_done': pack.product_qty})
                pick.action_done()
            else:
                pick.action_assign()
                if pick.state == 'assigned':
                    for pack in pick.pack_operation_ids:
                        pack.write({'qty_done': pack.product_qty})
                    pick.action_done() #TODO why action done and not do_new_transfer as button Validate does
        
        return True

    @api.multi
    def action_view_delivery(self):
        '''
        This function returns an action that display existing delivery orders
        of given pos sales order ids. It can either be a in a list or in a form
        view, if there is only one delivery order to show.
        '''
        action = self.env.ref('stock.action_picking_tree_all')

        result = {
            'name': action.name,
            'help': action.help,
            'type': action.type,
            'view_type': action.view_type,
            'view_mode': action.view_mode,
            'target': action.target,
            'context': action.context,
            'res_model': action.res_model,
        }

        pick_ids = sum([[order.picking_id.id] for order in self], [])

        if len(pick_ids) > 1:
            result['domain'] = "[('id','in',["+','.join(map(str, pick_ids))+"])]"
        elif len(pick_ids) == 1:
            form = self.env.ref('stock.view_picking_form', False)
            form_id = form.id if form else False
            result['views'] = [(form_id, 'form')]
            result['res_id'] = pick_ids[0]
        return result

class ProcurementOrder(models.Model):
    _inherit = 'procurement.order'
    
    pos_line_id = fields.Many2one('pos.order.line', string='Pos Order Line')
