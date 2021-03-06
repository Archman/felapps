"""Subclass of DataScanFrame, which is generated by wxFormBuilder."""

import wx
from . import datascanframe_ui as dsfui

import epics
import time
from datetime import datetime
import numpy as np

from .uiutils import EditListFrame, EditFrame
from .funutils import ScanDataFactor, set_staticbmp_color, pick_color
from .funclistframe import FuncListFrame


# Implementing DataScanFrame
class DataScanFrame(dsfui.DataScanFrame):
    def __init__(self, parent):
        dsfui.DataScanFrame.__init__(self, parent)

        self._post_init()
        self._post_set_scan()
        self._init_timers()

    # user-defined event:
    def _post_init(self):
        # scan range objs
        self.scan_range_objs = [
            self.var1_from_st, self.var1_from_tc, self.var1_to_st,
            self.var1_to_tc
        ]
        # pv list objs
        self.pv_list_objs = [
            self.daq_pv_list_st, self.daq_pv_list_tc, self.daq_pv_list_btn
        ]

        # advance mode
        self.adv_mode_btn.Disable()
        self.adv_mode_ckb.SetValue(False)

        # daq mode
        [obj.Disable() for obj in self.pv_list_objs]

        # post-operation onto data from var-II PV
        self.var2_op_dict = {
            'none': self._op_none,
            'sum': self._op_sum,
            'max': self._op_max,
            'min': self._op_min,
            'user-defined': self._op_other,
        }
        self._user_func = []  # user defined functions

        # define var1 set operation
        self.var1_set_dict = {
            'none': self._set_none,
            'user-defined': self._set_other,
        }

        # set up scan_flag, 'xyscan' or 'daq'
        self.scan_flag = {
            True: 'xyscan',
            False: 'daq'
        }[self.ds_flag_rb.GetValue()]

        # mode_tc, also will be writtne into scan logs
        # font facename: monospace
        mfont = self.mode_tc.GetFont()
        mfont.SetFaceName('Monospace')
        self.mode_tc.SetFont(mfont)
        self.mode_tc.SetDefaultStyle(wx.TextAttr(wx.BLACK))
        self.mode_tc.SetValue('Parameters scan mode is activated.\n')
        self.mode_tc.AppendText('-' * 20 + '\n')

        # default var2_op_func:
        self.var2_op_func = lambda x: x

        # default var1_set_func:
        self.var1_set_func = lambda x, pvobj: pvobj.put(x)

        # default path for user-defined functions
        self.func_path = '.'

        # fit control
        # models
        fit_model_list = ['gaussian', 'polynomial', 'none']
        self.fit_model_cb.Clear()
        self.fit_model_cb.AppendItems(fit_model_list)
        self.fit_model_cb.SetValue('none')

        # scan figure style control
        # line choice
        lineidlist = ['Average Curve', 'Errorbars', 'Fitting Curve']
        self.lineid_cb.Clear()
        self.lineid_cb.AppendItems(lineidlist)
        self.lineid_cb.SetValue('Average Curve')

        # line style
        lslist = ['solid', 'dashed', 'dashdot', 'dotted', 'none']
        self.ls_cb.Clear()
        self.ls_cb.AppendItems(lslist)
        self.ls_cb.SetValue('solid')

        # marker style
        mk_dict = {
            'none': {
                'code': u'none',
                'symbol': ''
            },
            'point': {
                'code': u'\N{BLACK CIRCLE}',
                'symbol': '.'
            },
            'circle': {
                'code': u'\N{WHITE CIRCLE}',
                'symbol': 'o'
            },
            'square': {
                'code': u'\N{WHITE LARGE SQUARE}',
                'symbol': 's'
            },
            'pentagon': {
                'code': u'\N{WHITE PENTAGON}',
                'symbol': 'p'
            },
            'hexagon1': {
                'code': u'\N{WHITE HEXAGON}',
                'symbol': 'h'
            },
            'diamond': {
                'code': u'\N{WHITE DIAMOND}',
                'symbol': 'D'
            },
            'tdiamond': {
                'code': u'\N{LOZENGE}',
                'symbol': 'd'
            },
            'star': {
                'code': u'\N{STAR OPERATOR}',
                'symbol': '*'
            },
            'cross': {
                'code': u'\N{VECTOR OR CROSS PRODUCT}',
                'symbol': 'x'
            },
            'plus': {
                'code': u'\N{PLUS SIGN}',
                'symbol': '+'
            },
            'hline': {
                'code': u'\N{MINUS SIGN}',
                'symbol': '_'
            },
            'vline': {
                'code': u'\N{DIVIDES}',
                'symbol': '|'
            },
            'tri_down': {
                'code': u'\N{WHITE DOWN-POINTING TRIANGLE}',
                'symbol': 'v'
            },
            'tri_up': {
                'code': u'\N{WHITE UP-POINTING TRIANGLE}',
                'symbol': '^'
            },
            'tri_right': {
                'code': u'\N{WHITE RIGHT-POINTING TRIANGLE}',
                'symbol': '>'
            },
            'tri_left': {
                'code': u'\N{WHITE LEFT-POINTING TRIANGLE}',
                'symbol': '<'
            },
        }
        self.mkstyle_cb.Clear()
        mk_code = [v['code'] for k, v in mk_dict.items()]
        self.mk_symbol = [v['symbol'] for k, v in mk_dict.items()]
        self.mkstyle_cb.AppendItems(mk_code)
        self.mkstyle_cb.SetValue('none')

        # lc, mec, mfc
        # average line: lc: wx.GREEN, mec: wx.BLUE, mfc: wx.BLUE
        # errorbar    : lc: wx.RED,   mec: wx.RED,  mfc: wx.RED
        set_staticbmp_color(self.lc_btn, wx.GREEN)
        set_staticbmp_color(self.mfc_btn, wx.BLUE)
        set_staticbmp_color(self.mec_btn, wx.BLUE)

        # fit_report_tc
        tfont = self.fit_report_tc.GetFont()
        tfont.SetFaceName('monospace')
        self.fit_report_tc.SetFont(tfont)

        # initial additional fitting parameters
        self.add_param_dict = {}

    def _post_set_scan(self):
        """ set scan configuration parameters
        """
        self.scaniternum_val = int(
            self.iternum_sc.GetValue())  # total number of scan points
        self.waitmsec_val = 1000.0 * float(self.waittime_sc.GetValue(
        ))  # time wait after every scan data setup, in millisecond
        self.shotnum_val = int(self.shotperiter_sc.GetValue(
        ))  # shots number to be recorded for each scan iteration
        self.scandaqfreq_val = int(
            self.daqrate_sc.GetValue())  # scan rep-rate [Hz]
        self.scandaqdelt_msec = 1000.0 / float(
            self.scandaqfreq_val)  # scan daq timer interval [ms]
        self.scandelt_msec = self.waitmsec_val + (
            self.shotnum_val + 1) * self.scandaqdelt_msec

        # debug only
        #print("iter:{iter}, shot#:{shot}, wait_t:{wt}, daq:{daq}".format(
        #    iter=self.scaniternum_val, shot=self.shotnum_val,
        #    wt=self.waitmsec_val, daq=self.scandaqfreq_val))

    def _init_timers(self):
        # tick timer
        fmt = '%Y-%m-%d %H:%M:%S %Z'
        self.timenow_st.SetLabel(time.strftime(fmt, time.localtime()))
        self.tick_timer = wx.Timer(self)
        self.Bind(wx.EVT_TIMER, self.tick_timerOnTimer, self.tick_timer)
        self.tick_timer.Start(1000)

        # scan ctrl timer
        self.scan_ctrl_timer = wx.Timer(self)
        self.Bind(wx.EVT_TIMER, self.scan_ctrl_timerOnTimer,
                  self.scan_ctrl_timer)

        # scan dq timer
        self.scan_daq_timer = wx.Timer(self)
        self.Bind(wx.EVT_TIMER, self.scan_daq_timerOnTimer,
                  self.scan_daq_timer)

    # menu items events leave to be implemented
    def save_mitemOnMenuSelection(self, event):
        pass

    def exit_mitemOnMenuSelection(self, event):
        pass

    def about_mitemOnMenuSelection(self, event):
        pass

    def tick_timerOnTimer(self, event):
        fmt = '%Y-%m-%d %H:%M:%S %Z'
        self.timenow_st.SetLabel(time.strftime(fmt, time.localtime()))

    def iternum_scOnSpinCtrl(self, event):
        self.scaniternum_val = int(self.iternum_sc.GetValue())
        self._post_set_scan()

    def shotperiter_scOnSpinCtrl(self, event):
        self.shotnum_val = int(event.GetEventObject().GetValue())
        self._post_set_scan()

    def waittime_scOnSpinCtrl(self, event):
        self.waitmsec_val = float(event.GetEventObject().GetValue())
        self._post_set_scan()

    def daqrate_scOnSpinCtrl(self, event):
        self.scandaqfreq_val = int(event.GetEventObject().GetValue())
        self._post_set_scan()

    def var1_pv_flag_ckbOnCheckBox(self, event):
        if self.var1_pv_flag_ckb.IsChecked():
            self.var1_pv_read_tc.SetValue(self.var1_pv_set_tc.GetValue())
        else:
            self.var1_pv_read_tc.SetValue('')

    def ds_flag_rbOnRadioButton(self, event):
        if self.ds_flag_rb.GetValue():
            [obj.Enable() for obj in self.scan_range_objs]
            [obj.Disable() for obj in self.pv_list_objs]
            self.mode_tc.SetDefaultStyle(wx.TextAttr(wx.BLACK))
            self.mode_tc.SetValue('Parameters scan mode is activated.\n')
            self.mode_tc.AppendText('-' * 20 + '\n')
            self.scan_flag = 'xyscan'

    def daq_flag_rbOnRadioButton(self, event):
        if self.daq_flag_rb.GetValue():
            [obj.Disable() for obj in self.scan_range_objs]
            [obj.Enable() for obj in self.pv_list_objs]
            self.mode_tc.SetDefaultStyle(wx.TextAttr(wx.BLACK))
            self.mode_tc.SetValue(
                'Data correlation analysis mode is activated.\n')
            self.mode_tc.AppendText('-' * 20 + '\n')
            self.scan_flag = 'daq'

    def var2_op_comboxOnCombobox(self, event):
        obj = self.var2_op_combox
        op_func, hint_text = self.var2_op_dict[obj.GetStringSelection()]()
        self.var2_op_st.SetLabel(hint_text)
        self.var2_op_func = op_func

    def var1_set_comboxOnCombobox(self, event):
        obj = self.var1_set_combox
        set_func = self.var1_set_dict[obj.GetStringSelection()]()
        self.var1_set_func = set_func

    def fit_model_cbOnCombobox(self, event):
        obj = event.GetEventObject()
        val = obj.GetStringSelection()
        self.fit_curve(val)

    def fit_config_ckbOnCheckBox(self, event):
        if self.fit_config_ckb.IsChecked():
            self.fit_config_btn.Enable()
        else:
            self.fit_config_btn.Disable()

    def fit_config_btnOnButtonClick(self, event):
        obj = event.GetEventObject()
        add_param_dict = self.add_param_dict
        init_string_list = [
            '='.join([str(k).strip(), str(v).strip()])
            for k, v in add_param_dict.items()
        ]
        frame = MyEditConfigFrame(self, init_string_list, label='Config List')
        frame.SetTitle('Additional Config')
        x, y = obj.GetScreenPosition()
        y += obj.GetSize()[1]
        frame.Show()
        frame.SetPosition((x, y))

    def fit_refresh_btnOnButtonClick(self, event):
        """ refresh fit
        """
        val = self.fit_model_cb.GetValue()
        if val != 'none':
            self.fit_curve(val)

    def fit_to_fig_btnOnButtonClick(self, event):
        """ stick fit result onto scan figure
        """
        self._stick_text()

    def stick_pos_tcOnTextEnter(self, event):
        if not hasattr(self.scanfig_panel, 'func_text'):
            self._stick_text()
        else:
            try:
                val = self.stick_pos_tc.GetValue()
                kws = {
                    k.strip(): float(v.strip())
                    for k, v in [i.split('=') for i in val.split(';')]
                }
            except:
                kws = {}
            self.scanfig_panel.update_text(**kws)

    def adv_mode_ckbOnCheckBox(self, event):
        if self.adv_mode_ckb.IsChecked():
            self.adv_mode_btn.Enable()
        else:
            self.adv_mode_btn.Disable()

    def var1_from_tcOnTextEnter(self, event):
        obj = event.GetEventObject()
        val = obj.GetValue()
        try:
            float(val)
        except:
            dial = wx.MessageDialog(
                self,
                message=u"Please input a number.",
                caption=u"Input Warning",
                style=wx.OK | wx.ICON_WARNING | wx.CENTRE)
            if dial.ShowModal() == wx.ID_OK:
                obj.SetValue('')
                dial.Destroy()

    def var1_to_tcOnTextEnter(self, event):
        obj = event.GetEventObject()
        val = obj.GetValue()
        try:
            float(val)
        except:
            dial = wx.MessageDialog(
                self,
                message=u"Please input a number.",
                caption=u"Input Warning",
                style=wx.OK | wx.ICON_WARNING | wx.CENTRE)
            if dial.ShowModal() == wx.ID_OK:
                obj.SetValue('')
                dial.Destroy()

    def var1_pv_tcOnTextEnter(self, event):
        obj = event.GetEventObject()
        pv_string = obj.GetValue()
        if not self._pv_check(pv_string):
            dial = wx.MessageDialog(
                self,
                message=u"Input PV: " + pv_string + " could not be reached.",
                caption=u"PV Warning",
                style=wx.OK | wx.ICON_WARNING | wx.CENTRE)
            if dial.ShowModal() == wx.ID_OK:
                dial.Destroy()

    def var2_pv_tcOnTextEnter(self, event):
        obj = event.GetEventObject()
        pv_string = obj.GetValue()
        if not self._pv_check(pv_string):
            dial = wx.MessageDialog(
                self,
                message=u"Input PV: " + pv_string + " could not be reached.",
                caption=u"PV Warning",
                style=wx.OK | wx.ICON_WARNING | wx.CENTRE)
            if dial.ShowModal() == wx.ID_OK:
                dial.Destroy()

    def start_btnOnButtonClick(self, event):
        # set log
        self.mode_tc.SetDefaultStyle(wx.TextAttr(wx.BLUE))
        self.mode_tc.AppendText("Initiate scan routine...\n")

        # set scan params
        self.set_scan_params()

        # debug only
        try:
            self.scanfig_panel.cla()
        except:
            pass

        # start timestamp
        self.start_timestamp = datetime.now()

        # start scan
        self.accum_scan_num = 0
        self.scan_ctrl_timer.Start(self.scandelt_msec)

    def stop_btnOnButtonClick(self, event):
        self.scan_ctrl_timer.Stop()
        self.scan_daq_timer.Stop()
        # set log
        self.mode_tc.SetDefaultStyle(wx.TextAttr(wx.GREEN))
        self.mode_tc.AppendText("Stop scan routine...\n")

    def retake_btnOnButtonClick(self, event):
        #print self.add_param_dict
        pick_pt = self.scanfig_panel.get_pick_pt()
        #a = self.scan_output_all
        #b = self.var1_range_array
        #for k,v in pick_pt.iteritems():
        #    print(k)
        #    print(b[k])
        #    print(a[self.shotnum_val*k:self.shotnum_val*(k+1)])
        #    print(a[self.shotnum_val*k:self.shotnum_val*(k+1)][:,0].mean())
        #    print(a[self.shotnum_val*k:self.shotnum_val*(k+1)][:,1].mean())

        retake_delt_msec = self.scandelt_msec
        self.retake_indice = pick_pt.keys()
        self.var1_idx_retake = 0
        self.var1_idx_retake_length = len(self.retake_indice)

        self.set_retake_flag()
        self.scan_ctrl_timer.Start(self.scandelt_msec)

    def set_retake_flag(self):
        """ set retake process flag
        """
        self.retake_flag = True

    def unset_retake_flag(self):
        self.retake_flag = False

    def daq_pv_list_btnOnButtonClick(self, event):
        obj = event.GetEventObject()
        init_string_list = self.daq_pv_list_tc.GetValue().split(';')
        frame = MyEditListFrame(self, init_string_list, 'PV List')
        frame.SetTitle('Make PV List')
        x, y = obj.GetScreenPosition()
        y += obj.GetSize()[1]
        frame.Show()
        frame.SetPosition((x, y))

    def scan_ctrl_timerOnTimer(self, event):
        """ scan procedure control timer
        """
        try:
            if not self.retake_flag:  # retake is not enabled
                #print "active normal process", self.var1_idx, self.var1_range_num
                assert self.var1_idx < self.var1_range_num
                # define the PUT action here
                # 1: the simplest case: directly put the value onto some PV
                #self.var1_set_PV.put(self.var1_range_array[self.var1_idx])
                # 2: general case: define the PUT action, should including case 1
                scanval = self.var1_range_array[self.var1_idx]
                #print self.var1_set_func
                self.var1_set_func(scanval, pvobj=self.var1_set_PV)
                #self._debug_check_pv(self.var1_set_PV)

                wx.MilliSleep(self.waitmsec_val)
                self.start_scan_daq_timer(self.scandaqdelt_msec, self.var1_idx)
                self.var1_idx += 1
            elif self.retake_flag:  # retake is enabled
                #print "active retake process", self.var1_idx_retake, self.var1_idx_retake_length
                assert self.var1_idx_retake < self.var1_idx_retake_length
                retake_idx = self.retake_indice[self.var1_idx_retake]
                self.var1_set_PV.put(self.var1_range_array[retake_idx])
                wx.MilliSleep(self.waitmsec_val)
                self.start_scan_daq_timer(self.scandaqdelt_msec, retake_idx)
                self.var1_idx_retake += 1
        except AssertionError:
            self.scan_ctrl_timer.Stop()
            self.scan_daq_timer.Stop()
            self.daq_cnt = 0
            self.unset_retake_flag()
            # set log
            self.mode_tc.SetDefaultStyle(wx.TextAttr(wx.BLUE))
            self.mode_tc.AppendText("Stop scan routine...\n")
            fmt = '%Y-%m-%d %H:%M:%S %Z'
            self.stop_timestamp = time.strftime(fmt, time.localtime())
            self.scan_time = '{dt:.1f}'.format(
                dt=(datetime.now() - self.start_timestamp).seconds)
            self.show_scandiag()

    def scan_daq_timerOnTimer(self, event):
        """ timer to control every scan iteration
        """
        self.scan_output_iter[self.daq_cnt, :] = self.var1_get_PV.get(
        ), self.var2_op_func(self.var2_get_PV.get())
        if self.daq_cnt == self.shotnum_val - 1:
            self.scan_daq_timer.Stop()
            # write scan log to mode_tc
            logmsg = 'Iter#: {0:>3d} is DONE, scan value: {1:<.3f}\n'.format(
                self.scan_idx_now + 1,
                self.var1_range_array[self.scan_idx_now])
            self.mode_tc.SetDefaultStyle(wx.TextAttr(wx.RED))
            self.mode_tc.AppendText(logmsg)
            self.scan_output_all[self.scan_idx_now * self.shotnum_val:(
                self.scan_idx_now + 1
            ) * self.shotnum_val, :] = self.scan_output_iter
            self.update_scanfigure()
        self.daq_cnt += 1
        self.accum_scan_num += 1

    # plot style configurations
    def lineid_cbOnCombobox(self, event):
        val = self.lineid_cb.GetValue()
        self.scanfig_panel.set_line_id(val)

    def mks_scOnSpinCtrl(self, event):
        obj = event.GetEventObject()
        val = obj.GetValue()
        self.scanfig_panel.set_mks(val)

    def mew_scOnSpinCtrl(self, event):
        obj = event.GetEventObject()
        val = obj.GetValue()
        self.scanfig_panel.set_mew(val)

    def lw_scOnSpinCtrl(self, event):
        obj = event.GetEventObject()
        val = obj.GetValue()
        self.scanfig_panel.set_linewidth(val)

    def lc_btnOnButtonClick(self, event):
        obj = event.GetEventObject()
        color = pick_color()
        if color is not None:
            c = color.GetAsString(wx.C2S_HTML_SYNTAX)
            self.scanfig_panel.set_linecolor(c)
            set_staticbmp_color(obj, color)

    def mec_btnOnButtonClick(self, event):
        obj = event.GetEventObject()
        color = pick_color()
        if color is not None:
            c = color.GetAsString(wx.C2S_HTML_SYNTAX)
            self.scanfig_panel.set_mec(c)
            set_staticbmp_color(obj, color)

    def mfc_btnOnButtonClick(self, event):
        obj = event.GetEventObject()
        color = pick_color()
        if color is not None:
            c = color.GetAsString(wx.C2S_HTML_SYNTAX)
            self.scanfig_panel.set_mfc(c)
            set_staticbmp_color(obj, color)

    def mkstyle_cbOnCombobox(self, event):
        obj = event.GetEventObject()
        idx = obj.GetSelection()
        new_mk = self.mk_symbol[idx]
        self.scanfig_panel.set_marker(new_mk)

    def ls_cbOnCombobox(self, event):
        obj = event.GetEventObject()
        new_ls = obj.GetStringSelection()
        self.scanfig_panel.set_linestyle(new_ls)

    def grid_ckbOnCheckBox(self, event):
        self.scanfig_panel.set_grid()

    def legend_ckbOnCheckBox(self, event):
        try:
            obj = event.GetEventObject()
            show_val = obj.GetValue()
            self.scanfig_panel.set_legend(avg=None, fit=None, show=show_val)
        except:
            pass

    def auto_xlabel_ckbOnCheckBox(self, event):
        try:
            obj = event.GetEventObject()
            user_xlabel = self.var1_get_PV.pvname + '\n' \
                        + '(scan dependent:' + self.var2_get_PV.pvname + ')'
            if self.user_xlabel_ckb.IsChecked():
                user_xlabel = self.user_xlabel_tc.GetValue()
            self.scanfig_panel.set_xlabel(
                show=obj.GetValue(), xlabel=user_xlabel)
        except:
            pass

    def user_xlabel_ckbOnCheckBox(self, event):
        if event.GetEventObject().IsChecked():
            self.user_xlabel_tc.Enable()
        else:
            self.user_xlabel_tc.Disable()

    def auto_title_ckbOnCheckBox(self, event):
        try:
            obj = event.GetEventObject()
            user_title = 'Completed at: ' + self.stop_timestamp + '\n' \
                         + 'SCAN TIME: ' + self.scan_time + ' sec'
            self._USER_TITLE = user_title
            if self.user_title_ckb.IsChecked():
                user_title = self.user_title_tc.GetValue().replace(
                    '$TITLE', self._USER_TITLE)
            self.scanfig_panel.set_title(show=obj.GetValue(), title=user_title)
        except:
            pass

    def user_title_ckbOnCheckBox(self, event):
        if event.GetEventObject().IsChecked():
            self.user_title_tc.Enable()
        else:
            self.user_title_tc.Disable()

    def clr_retake_btnOnButtonClick(self, event):
        self.scanfig_panel.clear_pick_pt()

    # user-defined methods
    def fit_curve(self, model='gaussian'):
        val = model
        try:
            x_fit_min = self.add_param_dict.get('xmin')
            x_fit_max = self.add_param_dict.get('xmax')
            xmin = float(x_fit_min) if x_fit_min is not None else None
            xmax = float(x_fit_max) if x_fit_max is not None else None

            if val == 'none':
                self.scanfig_panel.hide_fit_line()
                return
            elif val == 'gaussian':
                self.scanfig_panel.set_fit_model(xmin=xmin, xmax=xmax)
            elif val == 'polynomial':
                n_order = self.add_param_dict.get('n')
                n = n_order if n_order is not None else 1
                self.scanfig_panel.set_fit_model(
                    model='polynomial', n=int(n), xmin=xmin, xmax=xmax)

            self.scanfig_panel.set_fit_line(xmin=xmin, xmax=xmax)
            self.fit_report(self.scanfig_panel.get_fit_model())
        except:
            pass

    def fit_report(self, fm):
        """ 
        fill fit_report_tc with curve fitting report
        """
        self.fit_report_tc.SetValue("-" * 30 + '\n')
        self.fit_report_tc.AppendText(fm.fit_report())

    def _pv_check(self, val):
        """ check if pv string of val is alive
        """
        if val == '':
            return False
        pv = epics.get_pv(val, connect=True, timeout=0.5)
        if pv.connected:
            return True
        else:
            return False

    def _op_none(self):
        hint_text = u"Raw data."
        op_func = lambda x: x
        return op_func, hint_text

    def _op_sum(self):
        hint_text = u"Integrate intensity."
        op_func = lambda x: np.sum(x)
        return op_func, hint_text

    def _op_max(self):
        hint_text = u"Get max number."
        op_func = lambda x: np.max(x)
        return op_func, hint_text

    def _op_min(self):
        hint_text = u"Get min number."
        op_func = lambda x: np.min(x)
        return op_func, hint_text

    def _op_other(self):
        hint_text = u"Use user-defined function."
        op_func = lambda x: x
        obj = self.var2_op_combox
        frame = FuncListFrame(self, self.func_path, 'op')
        frame.SetTitle('Select User-defined Function')
        x, y = obj.GetScreenPosition()
        y += obj.GetSize()[1]
        frame.Show()
        frame.SetPosition((x, y))
        return op_func, hint_text

    def _set_none(self):
        set_func = lambda x, pvobj: pvobj.put(x)
        return set_func

    def _set_other(self):
        set_func = lambda x, pvobj: pvobj.put(x)
        obj = self.var1_set_combox
        frame = FuncListFrame(self, self.func_path, 'set')
        frame.SetTitle('Select User-defined Function')
        x, y = obj.GetScreenPosition()
        y += obj.GetSize()[1]
        frame.Show()
        frame.SetPosition((x, y))
        return set_func

    def set_scan_params(self):
        """set up scan parameters, var1(x) and var2(y)
        """
        self.unset_retake_flag()

        if self.scan_flag == 'xyscan':
            self._set_xyvars()

        elif self.scan_flag == 'daq':
            # do daq
            pass

    def _set_xyvars(self):
        # scan variable, var1
        self.var1_set_PV = epics.PV(self.var1_pv_set_tc.GetValue())
        self.var1_get_PV = epics.PV(self.var1_pv_read_tc.GetValue())
        self.var1_range_min = float(self.var1_from_tc.GetValue())
        self.var1_range_max = float(self.var1_to_tc.GetValue())
        self.var1_range_num = self.scaniternum_val

        self.var1_range_array = np.linspace(
            self.var1_range_min, self.var1_range_max, self.var1_range_num)
        self.var1_idx = 0  # initial index of var1_range_array

        # scan dependent variable, var2
        self.var2_get_PV = epics.PV(self.var2_pv_tc.GetValue())

        # construct n x 2 array to put scan output, where n is the total record number
        # n = iteration_num x shot_num_per_iteration
        # scan_output_all : numpy array for all records,
        # scan_output_iter: numpy array for one iteration

        #self.scan_output_all = np.zeros((self.var1_range_num * self.shotnum_val, 2))
        total_num = self.var1_range_num * self.shotnum_val
        self.scan_output_all = np.array([[np.nan, np.nan]] * total_num)
        self.scan_output_iter = np.zeros((self.shotnum_val, 2))

    def start_scan_daq_timer(self, ms, scanidx):
        self.scan_idx_now = scanidx
        self.daq_cnt = 0
        self.scan_daq_timer.Start(ms)

    def update_scanfigure(self):
        """ update figure plot
        """
        scandata_ins = ScanDataFactor(self.scan_output_all,
                                      self.var1_range_num, self.shotnum_val)
        xerr_ins = scandata_ins.getXerrbar()
        yerr_ins = scandata_ins.getYerrbar()
        #idx = scandata_ins.getYavg()
        self.scanfig_panel.x = scandata_ins.getXavg()
        self.scanfig_panel.y = scandata_ins.getYavg()
        self.scanfig_panel.xerrarr = xerr_ins
        self.scanfig_panel.yerrarr = yerr_ins
        self.scanfig_panel.repaint()

    def show_scandiag(self):
        """ show dialog when scan is done
        """
        dial = wx.MessageDialog(
            self,
            message=
            "Finish data scan analysis.\nApply proper curve fitting and Save data by CTRL+S.",
            caption='Scan Done',
            style=wx.OK | wx.CENTRE | wx.ICON_QUESTION)
        if dial.ShowModal() == wx.ID_OK:
            dial.Destroy()

    def _stick_text(self):
        """ write fitting text information onto figure
        """
        fm = self.scanfig_panel.get_fit_model()
        text = fm.fit_report()
        fx, ft = fm.get_fitfunc()
        text = '\n'.join([ft['func'], ft['fcoef']])
        val = self.stick_pos_tc.GetValue()
        try:
            kws = {
                k.strip(): float(v.strip())
                for k, v in [i.split('=') for i in val.split(';')]
            }
        except:
            kws = {}
        self.scanfig_panel.set_text(text, **kws)

    def _debug_check_pv(self, pv):
        """ check the get PV value, debug only
        
        :param pv: pyepics PV object, i.e. created by epics.PV(EPICS_pv_string_name)
        """
        print(pv.get())

    #def


class MyEditListFrame(EditListFrame):
    def __init__(self, parent, string_list=None, label=None):
        EditListFrame.__init__(self, parent, string_list, label)

    def on_ok(self, event):
        str_list = self.elb.GetStrings()
        self.parent.daq_pv_list_tc.SetValue(';'.join(str_list))
        self.Close()


class MyEditConfigFrame(EditListFrame):
    def __init__(self, parent, string_list=None, label=None):
        EditListFrame.__init__(self, parent, string_list, label)

    def on_ok(self, event):
        str_list = self.elb.GetStrings()
        self.parent.add_param_dict = {
            k: v
            for k, v in [i.split('=') for i in str_list]
        }
        self.Close()


class MyEditFrame(EditListFrame):
    def __init__(self, parent, string_list=None, label=None):
        EditFrame.__init__(self, parent, string_list, label)

    def on_ok(self, event):
        self.parent._user_func = self.elb.GetStrings()
        self.Close()
