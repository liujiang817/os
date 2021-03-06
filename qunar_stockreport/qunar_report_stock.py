# -*- encoding: utf-8 -*-
##############################################################################
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as published
#    by the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see http://www.gnu.org/licenses/.
#
##############################################################################

from openerp import fields,api,_,models
from openerp import tools
from openerp.osv import osv,fields as fieldss
from openerp.exceptions import except_orm
from datetime import datetime

class qunar_report_stock_wizard(models.Model):
	_name = "qunar.report.stock.wizard"

	usage = fields.Selection([('period','Period'),('custom',_('Custom'))],'Usage')
	period = fields.Many2one('account.period','Period')
	date_start = fields.Date('Date Start')
	date_stop = fields.Date('Date Stop')
	stock_location = fields.Many2one('stock.location','Location',required=True)
	method = fields.Selection([('average','Average'),('fifo','FIFO')],string="Method")

	_defaults={
		'usage':'period',
		'method':'average',
		'date_stop':datetime.strftime(datetime.now(),'%Y-%m-%d')
	}

	@api.cr_uid_ids_context 
	def btn_query(self,cr,uid,ids,context=None):
		#get inventory location
		scrapped_ids = self.pool.get('stock.location').search(cr,uid,[('usage','=','inventory')],context=context)
		if not len(scrapped_ids):
			raise except_orm(_('Error!'),_("Scrapped Location Doesn't Exists!"))

		sc_id = self.pool.get('ir.model.data').xmlid_to_res_id(cr,uid,'stock.stock_location_scrapped')
		stock_id = self.browse(cr,uid,ids,context=context).stock_location.id
		wizd = self.browse(cr,uid,ids,context=context)

		if wizd.period:
			date_start = wizd.period.date_start
			date_stop = wizd.period.date_stop
		else:
			date_start = wizd.date_start
			date_stop = wizd.date_stop

		l_date_stop = date_start

		tools.drop_view_if_exists(cr,'qunar_report_stock_line')
		sqlstr = '''CREATE OR REPLACE VIEW qunar_report_stock_line AS (select row_number() OVER () as id, 
		t.id product_id,pt.categ_id product_cate,
		lt.remainder_qty as last_remainder,
		lt.remainder_amt as last_amt,
		(case when i.qty is null then 0 else i.qty end)+(case when pi.qty is null then 0 else pi.qty end) as in_stock_qty,
		(case when i.amt is null then 0 else i.amt end)+(case when pi.amt is null then 0 else pi.amt end) as in_stock_amt,
		(case when o.qty is null then 0 else o.qty end)+(case when po.qty is null then 0 else po.qty end) as out_stock_qty,
		(case when o.amt is null then 0 else o.amt end)+(case when po.amt is null then 0 else po.amt end) as out_stock_amt,
		case when pi.qty is null then 0 else pi.qty end as inventory_over_qty,
		case when pi.amt is null then 0 else pi.amt end as inventory_over_amt,
		case when po.qty is null then 0 else po.qty end as inventory_short_qty,
		case when po.amt is null then 0 else po.amt end as inventory_short_amt,
		lt.remainder_qty+(case when i.qty is null then 0 else i.qty end)+(case when pi.qty is null then 0 else pi.qty end)-(case when o.qty is null then 0 else o.qty end)-(case when po.qty is null then 0 else po.qty end) as remainder_qty,
		lt.remainder_amt+(case when i.amt is null then 0 else i.amt end)+(case when pi.amt is null then 0 else pi.amt end)-(case when o.amt is null then 0 else o.amt end)-(case when po.amt is null then 0 else po.amt end) as remainder_amt
		from 
		product_product t
		left join
		(select p.id,sum(s.product_uom_qty/u.factor) qty,sum(s.product_uom_qty*s.price_unit) amt 
		from stock_move s
		left join product_product p on s.product_id = p.id
		left join stock_location l on s.location_id = l.id and (l.usage ='internal' or s.location_id!=%(scrapped)s)
		inner join product_uom u on s.product_uom = u.id
		where 
		s.location_dest_id = %(stock)s and
		s.state='done' and 
		s.date >= '%(date_start)s' and s.date < '%(date_stop)s'
		group by p.id) i on t.id = i.id
		left join
		(select p.id,sum(s.product_uom_qty/u.factor) qty,sum(s.product_uom_qty*s.price_unit) amt 
		from stock_move s
		left join product_product p on s.product_id = p.id
		inner join stock_location l on s.location_dest_id = l.id and (l.usage ='internal' or s.location_dest_id!=%(scrapped)s)
		inner join product_uom u on s.product_uom = u.id
		where 
		s.location_id = %(stock)s and
		s.state='done' and 
		s.date >= '%(date_start)s' and s.date < '%(date_stop)s'
		group by p.id) o on t.id=o.id 
		left join 
		(select p.id,sum(s.product_uom_qty/u.factor) qty,sum(s.product_uom_qty*s.price_unit) amt 
		from stock_move s
		left join product_product p on s.product_id = p.id
		inner join product_uom u on s.product_uom = u.id
		where 
		s.location_id = %(scrapped)s 
		and s.location_dest_id=%(stock)s 
		and s.state='done' 
		and s.date >= '%(date_start)s' and s.date < '%(date_stop)s'
		group by p.id) pi on t.id=pi.id
		left join 
		(select p.id,sum(s.product_uom_qty/u.factor) qty,sum(s.product_uom_qty*s.price_unit) amt 
		from stock_move s
		left join product_product p on s.product_id = p.id
		inner join product_uom u on s.product_uom = u.id
		where 
		s.location_id = %(stock)s 
		and s.location_dest_id=%(scrapped)s
		and s.state='done' 
		and s.date >= '%(date_start)s' and s.date < '%(date_stop)s'
		group by p.id) po on t.id=po.id 
		left join
			(select  
			t.id product_id,
			(case when i.qty is null then 0 else i.qty end)+(case when pi.qty is null then 0 else pi.qty end)-(case when o.qty is null then 0 else o.qty end)-(case when po.qty is null then 0 else po.qty end) as remainder_qty,
			(case when i.amt is null then 0 else i.amt end)+(case when pi.amt is null then 0 else pi.amt end)-(case when o.amt is null then 0 else o.amt end)-(case when po.amt is null then 0 else po.amt end) as remainder_amt
			from 
			product_product t
			left join
			(select p.id,sum(s.product_uom_qty/u.factor) qty,sum(s.product_uom_qty*s.price_unit) amt 
			from stock_move s
			left join product_product p on s.product_id = p.id
			inner join stock_location l on s.location_id = l.id and (l.usage ='internal' or s.location_id!=%(scrapped)s)
			inner join product_uom u on s.product_uom = u.id 
			where 
			s.location_dest_id = %(stock)s and
			s.state='done' and  s.date < '%(l_date_stop)s'
			group by p.id) i on t.id = i.id
			left join
			(select p.id,sum(s.product_uom_qty/u.factor) qty,sum(s.product_uom_qty*s.price_unit) amt 
			from stock_move s
			left join product_product p on s.product_id = p.id
			inner join stock_location l on s.location_dest_id = l.id and (l.usage ='internal' or s.location_dest_id!=%(scrapped)s)
			inner join product_uom u on s.product_uom = u.id
			where 
			s.location_id = %(stock)s and
			s.state='done'  
			and s.date < '%(l_date_stop)s'
			group by p.id) o on t.id=o.id 
			left join 
			(select p.id,sum(s.product_uom_qty/u.factor) qty,sum(s.product_uom_qty*s.price_unit) amt 
			from stock_move s
			left join product_product p on s.product_id = p.id
			inner join product_uom u on s.product_uom = u.id
			where 
			s.location_id = %(scrapped)s 
			and s.location_dest_id=%(stock)s
			and s.state='done' 
			and s.date < '%(l_date_stop)s'
			group by p.id) pi on t.id=pi.id
			left join 
			(select p.id,sum(s.product_uom_qty/u.factor) qty,sum(s.product_uom_qty*s.price_unit) amt 
			from stock_move s
			left join product_product p on s.product_id = p.id
			inner join product_uom u on s.product_uom = u.id
			where 
			s.location_id = %(stock)s 
			and s.location_dest_id=%(scrapped)s
			and s.state='done' 
			and s.date < '%(l_date_stop)s'
			group by p.id) po on t.id=po.id) lt on t.id=lt.product_id
			left join
			product_template pt on t.product_tmpl_id = pt.id
            where t.active='t')
		
			'''

		sqlstr2 = '''CREATE OR REPLACE VIEW qunar_report_stock_line AS (select row_number() OVER () as id, 
		t.id product_id,pt.categ_id product_cate,
		lt.remainder_qty as last_remainder,
		lt.remainder_qty*ppl.price as last_amt,
		(case when i.qty is null then 0 else i.qty end) as in_stock_qty,
		(case when i.qty*ppl.price is null then 0 else i.qty*ppl.price end) as in_stock_amt,
		(case when o.qty is null then 0 else o.qty end) as out_stock_qty,
		(case when o.qty*ppl.price is null then 0 else o.qty*ppl.price end) as out_stock_amt,
		case when pi.qty is null then 0 else pi.qty end as inventory_over_qty,
		case when pi.qty*ppl.price is null then 0 else pi.qty*ppl.price end as inventory_over_amt,
		case when po.qty is null then 0 else po.qty end as inventory_short_qty,
		case when po.qty*ppl.price is null then 0 else po.qty*ppl.price end as inventory_short_amt,
		lt.remainder_qty+(case when i.qty is null then 0 else i.qty end)-(case when o.qty is null then 0 else o.qty end) as remainder_qty,
		lt.remainder_qty*ppl.price+(case when i.qty*ppl.price is null then 0 else i.qty*ppl.price end)-(case when o.qty*ppl.price is null then 0 else o.qty*ppl.price end) as remainder_amt
		from 
		product_product t
		left join
		(select p.id,sum(s.product_uom_qty/u.factor) qty,sum(s.product_uom_qty*s.price_unit) amt 
		from stock_move s
		left join product_product p on s.product_id = p.id
		left join stock_location l on s.location_id = l.id and (l.usage ='internal' or s.location_id!=%(scrapped)s)
		inner join product_uom u on s.product_uom = u.id
		where 
		s.location_dest_id = %(stock)s and
		s.state='done' and 
		s.date >= '%(date_start)s' and s.date < '%(date_stop)s'
		group by p.id) i on t.id = i.id
		left join
		(select p.id,sum(s.product_uom_qty/u.factor) qty,sum(s.product_uom_qty*s.price_unit) amt 
		from stock_move s
		left join product_product p on s.product_id = p.id
		inner join stock_location l on s.location_dest_id = l.id and (l.usage ='internal' or s.location_dest_id!=%(scrapped)s)
		inner join product_uom u on s.product_uom = u.id
		where 
		s.location_id = %(stock)s and
		s.state='done' and 
		s.date >= '%(date_start)s' and s.date < '%(date_stop)s'
		group by p.id) o on t.id=o.id 
		left join 
		(select p.id,sum(s.product_uom_qty/u.factor) qty,sum(s.product_uom_qty*s.price_unit) amt 
		from stock_move s
		left join product_product p on s.product_id = p.id
		inner join product_uom u on s.product_uom = u.id
		where 
		s.location_id = %(scrapped)s 
		and s.location_dest_id=%(stock)s 
		and s.state='done' 
		and s.date >= '%(date_start)s' and s.date < '%(date_stop)s'
		group by p.id) pi on t.id=pi.id
		left join 
		(select p.id,sum(s.product_uom_qty/u.factor) qty,sum(s.product_uom_qty*s.price_unit) amt 
		from stock_move s
		left join product_product p on s.product_id = p.id
		inner join product_uom u on s.product_uom = u.id
		where 
		s.location_id = %(stock)s 
		and s.location_dest_id=%(scrapped)s
		and s.state='done' 
		and s.date >= '%(date_start)s' and s.date < '%(date_stop)s'
		group by p.id) po on t.id=po.id 
		left join
			(select  
			t.id product_id,
			(case when i.qty is null then 0 else i.qty end)+(case when pi.qty is null then 0 else pi.qty end)-(case when o.qty is null then 0 else o.qty end)-(case when po.qty is null then 0 else po.qty end) as remainder_qty,
			(case when i.amt is null then 0 else i.amt end)+(case when pi.amt is null then 0 else pi.amt end)-(case when o.amt is null then 0 else o.amt end)-(case when po.amt is null then 0 else po.amt end) as remainder_amt
			from 
			product_product t
			left join
			(select p.id,sum(s.product_uom_qty/u.factor) qty,sum(s.product_uom_qty*s.price_unit) amt 
			from stock_move s
			left join product_product p on s.product_id = p.id
			inner join stock_location l on s.location_id = l.id and (l.usage ='internal' or s.location_id!=%(scrapped)s)
			inner join product_uom u on s.product_uom = u.id
			where 
			s.location_dest_id = %(stock)s and
			s.state='done' and  s.date < '%(l_date_stop)s'
			group by p.id) i on t.id = i.id
			left join
			(select p.id,sum(s.product_uom_qty/u.factor) qty,sum(s.product_uom_qty*s.price_unit) amt 
			from stock_move s
			left join product_product p on s.product_id = p.id
			inner join stock_location l on s.location_dest_id = l.id and (l.usage ='internal' or s.location_dest_id!=%(scrapped)s)
			inner join product_uom u on s.product_uom = u.id
			where 
			s.location_id = %(stock)s and
			s.state='done'  
			and s.date < '%(l_date_stop)s'
			group by p.id) o on t.id=o.id 
			left join 
			(select p.id,sum(s.product_uom_qty/u.factor) qty,sum(s.product_uom_qty*s.price_unit) amt 
			from stock_move s
			left join product_product p on s.product_id = p.id
			inner join product_uom u on s.product_uom = u.id
			where 
			s.location_id = %(scrapped)s 
			and s.location_dest_id=%(stock)s
			and s.state='done' 
			and s.date < '%(l_date_stop)s'
			group by p.id) pi on t.id=pi.id
			left join 
			(select p.id,sum(s.product_uom_qty/u.factor) qty,sum(s.product_uom_qty*s.price_unit) amt 
			from stock_move s
			left join product_product p on s.product_id = p.id
			inner join product_uom u on s.product_uom = u.id
			where 
			s.location_id = %(stock)s 
			and s.location_dest_id=%(scrapped)s
			and s.state='done' 
			and s.date < '%(l_date_stop)s'
			group by p.id) po on t.id=po.id) lt on t.id=lt.product_id
			left join
			product_template pt on t.product_tmpl_id = pt.id
			left join
			(select value_float price,to_number(split_part(res_id,',',2),'9999999999') t_id 
from ir_property where name='standard_price') ppl on pt.id = ppl.t_id
            where t.active='t')
		
			'''

		if wizd.method=="average":
			sqlstr = sqlstr2

		sqlstr = sqlstr % {'stock':stock_id,'scrapped':sc_id,'date_start':date_start+' 0:00:00','date_stop':date_stop+' 23:59:59','l_date_stop':l_date_stop+' 0:00:00'}

		cr.execute(sqlstr)
		res = {
			'name':_('Stock Report ')+ (wizd.period and wizd.period.name or date_start+'-'+date_stop),
			'res_model':'qunar.report.stock.line',
			'view_mode':'tree,form',
			'type':'ir.actions.act_window',
			}

		return res


class qunar_report_stock_line(osv.osv):
	_name="qunar.report.stock.line"
	_auto = False

	def _get_remainder(self,cr,uid,ids,name,args,context):
		res={}
		for line in self.browse(cr,uid,ids,context):
			res[line.id] = line.last_amt + line.in_stock_amt  - line.out_stock_amt 
		return res


	_columns={
		'product_id':fieldss.many2one('product.product','Product'),
		'product_cate': fieldss.many2one('product.category','Product Category'),
		'uom':fieldss.related('product_id','uom_id',type="many2one",relation="product.uom",string='Unit'),
		'last_remainder':fieldss.float('Init Qty'),	
		'last_amt':fieldss.float('Init Amount'),
		'in_stock_qty': fieldss.float('In Stock Quantity'),
		'in_stock_amt': fieldss.float('In Stock Amount'),
		'out_stock_qty': fieldss.float('Out Stock Quantity'),
		'out_stock_amt': fieldss.float('Out Stock Amount'),
		'inventory_short_qty': fieldss.float('Inventory Short Quantity'),
		'inventory_short_amt': fieldss.float('Inventory Short Amount'),
		'inventory_over_qty': fieldss.float('Inventory Over Quantity'),
		'inventory_over_amt': fieldss.float('Inventory Over Amount'),
		'remainder_qty': fieldss.float('Remainder Qty'),
		'remainder_amt': fieldss.float('Remainder Amount'),
	}