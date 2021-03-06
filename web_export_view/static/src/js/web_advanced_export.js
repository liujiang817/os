//  @@@ web_export_view custom JS @@@
//#############################################################################
//    
//    Copyright (C) 2012 Agile Business Group sagl (<http://www.agilebg.com>)
//    Copyright (C) 2012 Therp BV (<http://therp.nl>)
//
//    Part of codes has been changed by Rainsoft(<kfx2007@163.com>)
//
//    This program is free software: you can redistribute it and/or modify
//    it under the terms of the GNU Affero General Public License as published
//    by the Free Software Foundation, either version 3 of the License, or
//    (at your option) any later version.
//
//    This program is distributed in the hope that it will be useful,
//    but WITHOUT ANY WARRANTY; without even the implied warranty of
//    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
//    GNU Affero General Public License for more details.
//
//    You should have received a copy of the GNU Affero General Public License
//    along with this program.  If not, see <http://www.gnu.org/licenses/>.
//
//#############################################################################
console.log('IN !!!');
openerp.web_export_views = function(instance, m) {

    var _t = instance.web._t,
    QWeb = instance.web.qweb;

    instance.web.Sidebar.include({
        redraw: function() {
			console.log('running........');
            var self = this;
            this._super.apply(this, arguments);
            self.$el.find('.oe_sidebar').append(QWeb.render('AddExportViewMain', {widget: self}));
            self.$el.find('.oe_sidebar_export_view_xls').on('click', self.on_sidebar_export_view_xls);
            self.$el.find('.oe_sidebar_export_view_xls_all').on('click', self.on_sidebar_export_view_xls_all);
        },
        /**
        *  all data export
        *  @ all = true
        */
        on_sidebar_export_view_xls_all: function(){
            var self = this;
            self.on_sidebar_export_view_xls_excute(true);
        },

        on_sidebar_export_view_xls: function(){
            var self = this;
            self.on_sidebar_export_view_xls_excute(false);
        },

        on_sidebar_export_view_xls_excute: function(all) {
            // Select the first list of the current (form) view
            // or assume the main view is a list view and use that
            var self = this,
            view = this.getParent(),
            children = view.getChildren();

            if (children) {
                children.every(function(child) {
                    if (child.field && child.field.type == 'one2many') {
                        if(child.$el.css('display') == 'none'){
                            return true;
                        }else{
                            var isHide = false;
                            child.$el.parents("div").each(function(){
                                if($(this).css('display') == 'none'){
                                    isHide = true;
                                 }
                            });
                            if(isHide){
                                return true;
                            }
                        }
                        view = child.viewmanager.views.list.controller;
                         isHasView = true;
                        return false; // break out of the loop
                    }
                    if (child.field && child.field.type == 'many2many') {

                         if(child.$el.css('display') == 'none'){
                            return true;
                        }else{
                            var isHide = false;
                            child.$el.parent("div").each(function(){
                                console.log(this);
                                if($(this).css('display') == 'none'){
                                    isHide = true;
                                 }
                            });
                            if(isHide){
                                return true;
                            }
                        }

                        view = child.list_view;
                         isHasView = true;
                        return false; // break out of the loop
                    }
                    return true;
                });
            }

            export_columns_keys = [];
            export_columns_names = [];

            if(!view){
                alert("很抱歉！当前页面没有可导出的列表！");
                return false;
            }
            $.each(view.visible_columns, function(){
                if(this.tag=='field'){
                    // non-fields like `_group` or buttons
                    export_columns_keys.push(this.id);
                    export_columns_names.push(this.string);
                }
            });
            rows = view.$el.find('.oe_list_content > tbody > tr');
            export_rows = [];
            $.each(rows,function(){
                $row = $(this);
                // find only rows with data
                if($row.attr('data-id')){
                    export_row = [];
                    checked = $row.find('th input[type=checkbox]').attr("checked");
                    if(all){
                        checked = "checked"
                    }

                    if (children && checked === "checked"){
                        $.each(export_columns_keys,function(){
                            cell = $row.find('td[data-field="'+this+'"]').get(0);
                            text = cell.text || cell.textContent || cell.innerHTML || "";
                            if (cell.classList.contains("oe_list_field_float")){
                                export_row.push(instance.web.parse_value(text, {'type': "float"}));
                            }
                            else if (cell.classList.contains("oe_list_field_boolean")){
                        	var data_id = $( '<div>' + cell.innerHTML + '</div>');
                                if(data_id.find('input').get(0).checked){
                                	export_row.push(_t("True"));
                                }
                                else {
                                	export_row.push(_t("False"));
                                }
                            }
                            else if (cell.classList.contains("oe_list_field_integer")){
                               export_row.push(parseInt(text));
                            }
                            else{
                               export_row.push(text.trim());
                            }
                        });
                        export_rows.push(export_row);
                    };
                }
            });
            $.blockUI();
            view.session.get_file({
                url: '/web/export/xls_view',
                data: {data: JSON.stringify({
                    model : view.model,
                    headers : export_columns_names,
                    rows : export_rows
                })},
                complete: $.unblockUI
            });
        }

    });

};
