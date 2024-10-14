# -*- coding: utf-8 -*-

from odoo import models, fields, api, Command, _
from odoo.exceptions import UserError
class MrpUnbuild(models.Model):
    _inherit = "mrp.unbuild"
    
    detailed_list_ids = fields.One2many(
        'mrp.build.detailed_line', 'unbuild_id',
        string='Detailed lists',
        compute='_compute_detailed_list',
        help='This lines are the ones the user has selected to be paid.',
        readonly=False,
        store=True
    )

    allow_adjustments = fields.Boolean(string='Permitir ajustes', default = True)

    @api.depends('bom_id','product_id')
    def _compute_detailed_list(self):
        for unbuild in self:
            if unbuild.bom_id:
               if unbuild.bom_id:
                # Limpia las líneas existentes y agrega nuevas con Command
                detailed_lines = self.env['mrp.build.detailed_line']
                for bom_line in unbuild.bom_id.bom_line_ids:
                    detailed_lines |= self.env['mrp.build.detailed_line'].create({
                        'product_id': bom_line.product_id.id,
                        'qty': bom_line.product_qty,
                        'unbuild_id': unbuild.id
                    })
                
                # Actualizar el campo One2many usando Command.clear() y Command.create()
                unbuild.detailed_list_ids = [
                    Command.clear(),  # Elimina todas las líneas anteriores
                    Command.set(detailed_lines.ids)  # Agrega las nuevas líneas
                ]
            else:
                 unbuild.detailed_list_ids = False
                
    def _generate_consume_moves(self):
        moves = self.env['stock.move']
        for unbuild in self:
            if unbuild.detailed_list_ids and unbuild.allow_adjustments:
                moves += unbuild._generate_move_from_bom_line(self.product_id, self.product_uom_id, unbuild.product_qty)
            elif unbuild.mo_id:
                finished_moves = unbuild.mo_id.move_finished_ids.filtered(lambda move: move.state == 'done')
                factor = unbuild.product_qty / unbuild.mo_id.product_uom_id._compute_quantity(unbuild.mo_id.qty_produced, unbuild.product_uom_id)
                for finished_move in finished_moves:
                    moves += unbuild._generate_move_from_existing_move(finished_move, factor, unbuild.location_id, finished_move.location_id)
            else:
                factor = unbuild.product_uom_id._compute_quantity(unbuild.product_qty, unbuild.bom_id.product_uom_id) / unbuild.bom_id.product_qty
                moves += unbuild._generate_move_from_bom_line(self.product_id, self.product_uom_id, unbuild.product_qty)
                for byproduct in unbuild.bom_id.byproduct_ids:
                    if byproduct._skip_byproduct_line(unbuild.product_id):
                        continue
                    quantity = byproduct.product_qty * factor
                    moves += unbuild._generate_move_from_bom_line(byproduct.product_id, byproduct.product_uom_id, quantity, byproduct_id=byproduct.id)
        return moves

    def _generate_produce_moves(self):
        moves = self.env['stock.move']
        for unbuild in self:
            if unbuild.detailed_list_ids and unbuild.allow_adjustments:
                for line in unbuild.detailed_list_ids:
                     moves += unbuild._generate_move_from_bom_line(line.product_id, line.product_uom_id, line.qty, isProduce=True)
            elif unbuild.mo_id:
                raw_moves = unbuild.mo_id.move_raw_ids.filtered(lambda move: move.state == 'done')
                factor = unbuild.product_qty / unbuild.mo_id.product_uom_id._compute_quantity(unbuild.mo_id.qty_produced, unbuild.product_uom_id)
                for raw_move in raw_moves:
                    moves += unbuild._generate_move_from_existing_move(raw_move, factor, raw_move.location_dest_id, self.location_dest_id)
            else:
                factor = unbuild.product_uom_id._compute_quantity(unbuild.product_qty, unbuild.bom_id.product_uom_id) / unbuild.bom_id.product_qty
                boms, lines = unbuild.bom_id.explode(unbuild.product_id, factor, picking_type=unbuild.bom_id.picking_type_id)
                for line, line_data in lines:
                    moves += unbuild._generate_move_from_bom_line(line.product_id, line.product_uom_id, line_data['qty'], bom_line_id=line.id)
        return moves

    def _generate_move_from_bom_line(self, product, product_uom, quantity, bom_line_id=False, byproduct_id=False, isProduce=False):
        product_prod_location = product.with_company(self.company_id).property_stock_production
        if self.detailed_list_ids and isProduce and self.allow_adjustments:
            location_id = product_prod_location
            location_dest_id = self.location_id
        else:
            location_id = bom_line_id and product_prod_location or self.location_id
            location_dest_id = bom_line_id and self.location_dest_id or product_prod_location
        warehouse = location_dest_id.warehouse_id
        return self.env['stock.move'].create({
            'name': self.name,
            'date': self.create_date,
            'bom_line_id': bom_line_id,
            'byproduct_id': byproduct_id,
            'product_id': product.id,
            'product_uom_qty': quantity,
            'product_uom': product_uom.id,
            'procure_method': 'make_to_stock',
            'location_dest_id': location_dest_id.id,
            'location_id': location_id.id,
            'warehouse_id': warehouse.id,
            'unbuild_id': self.id,
            'company_id': self.company_id.id,
        })

class MRPDetailedLine(models.Model):
    _name = 'mrp.build.detailed_line'

    product_id = fields.Many2one(
         comodel_name='product.product',
         string='Product', 
    )
    qty = fields.Float('quantity')
    
    product_uom_id = fields.Many2one(
    comodel_name='uom.uom',  # Modelo de unidades de medida
    string='Unit of Measure', 
    related='product_id.uom_id',  # Se refiere al UOM del producto seleccionado
    readonly=True,  # Se establece como solo lectura para que no pueda modificarse manualmente
    store=True  # Se almacena en la base de datos para mejorar el rendimiento
    )

    unbuild_id = fields.Many2one(
        comodel_name='mrp.unbuild',
        string='Unbuild Order',
        ondelete='cascade'  # Esto asegura que los registros detallados se eliminen si se elimina el registro principal
    )