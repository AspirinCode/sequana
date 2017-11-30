# coding: utf-8
#
#  This file is part of Sequana software
#
#  Copyright (c) 2016 - Sequana Development Team
#
#  File author(s):
#      Dimitri Desvillechabrol <dimitri.desvillechabrol@pasteur.fr>,
#          <d.desvillechabrol@gmail.com>
#
#  Distributed under the terms of the 3-clause BSD license.
#  The full license is in the LICENSE file, distributed with this software.
#
#  website: https://github.com/sequana/sequana
#  documentation: http://sequana.readthedocs.io
#
##############################################################################
"""Module to write joint calling report"""
from sequana.modules_report.base_module import SequanaBaseModule
from sequana.utils.datatables_js import DataTable


class JointCallingModule(SequanaBaseModule):
    """ Write HTML report of variant calling. This class takes a csv file
    generated by sequana_variant_filter.
    """
    def __init__(self, data):
        """.. rubric:: constructor

        :param data: it can be a csv filename created by
        sequana.freebayes_vcf_filter or a
        :class:`freebayes_vcf_filter.Filtered_freebayes` object.
        """
        super().__init__(template_fn='joint_calling.html')
        self.title = "Joint Calling Report"
        self.vcf = data
        self.table_html, self.table_options = self.create_datatable()
        self.create_html('joint_calling.html')

    def create_datatable(self):
        """ Variants detected section.
        """
        datatable = DataTable(self.vcf.df, 'jc')
        datatable.datatable.datatable_options = {
                'scrollX': 'true',
                'pageLength': 15,
                'scrollCollapse': 'true',
                'dom': 'Bfrtip',
                'buttons': ['copy', 'csv']
        }
        for i, s in enumerate(self.vcf.vcf.samples):
            datatable.datatable.set_tooltips_to_column('info_{0}'.format(i), s)
        options = datatable.datatable._create_datatable_option()
        html_tab = datatable._create_hidden_csv(float_format='%.3f')
        html_tab += datatable._create_html_table(style='width: 100%;')
        return html_tab, options
