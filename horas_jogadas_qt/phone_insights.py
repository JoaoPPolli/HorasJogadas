"""Páginas de detalhes e retrospectiva para o painel conectado, sem expor caminhos."""
import base64
from horas_jogadas import i18n
from .insights import game_details,recap,available_years,recap_filename
from .recap_image import png_bytes
from .detection import profiles
from . import preferences
from .remote_server import RemoteError

class PhoneInsights:
    def __init__(self,control):self.control=control
    @property
    def w(self):return self.control.window
    def period(self,values):
        try:
            year=values.get('year');month=values.get('month',0)
            if isinstance(year,str) and year.isascii() and year.isdigit():year=int(year)
            if isinstance(month,str) and month.isascii() and month.isdigit():month=int(month)
            if type(year) is not int or type(month) is not int:raise ValueError()
            if not 1900<=year<=9999 or not 0<=month<=12:raise ValueError()
            return year,month
        except (ValueError,TypeError):raise RemoteError(400,'invalid') from None
    def view(self,page,values):
        if page=='game':
            key=values.get('id')
            if not isinstance(key,str) or key not in self.w.c.timers:raise RemoteError(404,'not_found')
            data=game_details(self.w.c,key);profile=profiles(self.w.c.folder).get(key,{})
            data['detection']=dict(configured=bool(profile.get('executable')),enabled=bool(profile.get('enabled')),active=bool(preferences.read(self.w.c.folder).get('detection_enabled',False)))
        else:
            year,month=self.period(values);key=values.get('game_id')
            if 'game_id' in values and (not isinstance(key,str) or key not in self.w.c.timers):raise RemoteError(404,'not_found')
            data=recap(self.w.c,year,month,key);data['years']=sorted(set(available_years(self.w.c,key))|{year},reverse=True)
            data['filename']=recap_filename(data)
        return dict(data,revision=self.control.workspace_revision())
    def preview(self,values):
        data=self.view('recap',values)
        return dict(data,image='data:image/png;base64,'+base64.b64encode(png_bytes(data,self.w.theme_name(),i18n.idioma_atual())).decode('ascii'))
    def export(self,values):
        data=self.view('recap',values)
        return png_bytes(data,self.w.theme_name(),i18n.idioma_atual()),'image/png',recap_filename(data)
