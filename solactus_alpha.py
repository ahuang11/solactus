import panel as pn
import numpy as np
import pandas as pd
import hvplot.pandas
import holoviews as hv

from holoviews import opts
from skyfield import api, almanac
from geopy.geocoders import Nominatim, GeoNames
from bokeh.models import DatetimeTickFormatter, HoverTool

hv.extension('bokeh')
hv.renderer('bokeh').theme = 'caliber'
ts = api.load.timescale()
e = api.load('de421.bsp')


def _format_datetime_axis(plot, element):
    p = plot.state
    p.xaxis.formatter = DatetimeTickFormatter(
        hours=["%b %d"],
        days=["%b %d"],
        months=["%b %d"],
        years=["%b %d"],
    )
    p.xaxis[0].ticker.desired_num_ticks = 10


def _compute_loc_sunset(input_str):
    geolocator = Nominatim(user_agent='sunset_app', timeout=3)
    geoloc = geolocator.geocode(input_str)
    lat, lon = geoloc.latitude, geoloc.longitude

    loc = api.Topos('{0} N'.format(lat), '{0} E'.format(lon))

    t0 = ts.utc(2020, 7, 1)
    t1 = ts.utc(2021, 7, 1)
    t, y = almanac.find_discrete(t0, t1, almanac.sunrise_sunset(e, loc))

    df = pd.DataFrame({'datetime': t.utc_iso(), 'sun_down': y})
    df['datetime'] = pd.to_datetime(df['datetime'])
    tz = GeoNames(username='zethiroth').reverse_timezone(
        (geoloc.latitude, geoloc.longitude))
    df['datetime'] = df['datetime'].dt.tz_localize(
        'utc').dt.tz_convert(tz.pytz_timezone)
    df['date'] = df['datetime'].dt.date
    df['time'] = df['datetime'].dt.time
    df['hour'] = (
        df['time'].astype(str).str.split(':', expand=True).astype(int).apply(
            lambda row: row[0] + row[1] / 60. + row[2] / 3600., axis=1)
    )
    df['hour_24'] = 240
    df['daylight'] = np.abs(df['hour'].diff().shift(-1))
    return df, geoloc


def _show_sunset_hour(df, geoloc):
    hover = HoverTool(
        tooltips=[
            ('Date', '@datetime{%m/%d}'),
            ('Hour of Sunset', '@hour{0.1f}'),
            ('Length of Day', '@daylight{0.1f}'),
        ],

        formatters={
            'datetime': 'datetime',
        },
        mode='vline'
    )

    sunset_df = df.copy()
    sunset_df = df.loc[df['sun_down'] == False, :]
    sunset_df = sunset_df.assign(**{'hour': sunset_df['hour'] - 12,
                                    'hour_24': sunset_df['hour_24'] - 12}) 

    lat, lon = geoloc.latitude, geoloc.longitude
    address = geoloc.address
    sunset_curve = sunset_df.hvplot('datetime', 'hour',
                                    hover_cols=['daylight'])
    sunset_curve = sunset_curve.opts(
        invert_yaxis=True, color='darkblue',
        xlabel='Date', ylabel='PM Hour of Sunset [Local Time]',
        title=f'Yearly Sunset Hour at {address} ({lat:.1f} N, {lon:.1f} E)',
        hooks=[_format_datetime_axis], show_grid=True,
        gridstyle={'ygrid_line_alpha': 0}, tools=[hover],
        width=925, height=500, ylim=(4, 9)
    )

    sun_up = hv.Area(df.loc[df['sun_down'] == False], 'datetime', 'hour')
    sun_up = sun_up.opts(color='tan', alpha=0.15)

    sun_down = hv.Area(sunset_df, 'datetime', ['hour', 'hour_24'])
    sun_down = sun_down.opts(color='darkblue', alpha=0.15)

    five_pm_line = hv.HLine(5).opts(color='black', alpha=0.1,
                                     line_dash='dotted')

    five_pm_txt = hv.Text(pd.datetime(2020, 7, 4), 5, '5 PM')
    five_pm_txt = five_pm_txt.opts(text_font_size='1.5em', text_alpha=0.2,
                                   text_baseline='bottom', text_align='left')

    overlay = (sunset_curve * sun_up * sun_down * five_pm_line * five_pm_txt)
    return overlay


def trigger(Location1=None, Location2=None):
    if Location1 is not None:
        return pn.Pane(_show_sunset_hour(*_compute_loc_sunset(Location1)),
                       name=f'Location 1')
    elif Location2 is not None:
        return pn.Pane(_show_sunset_hour(*_compute_loc_sunset(Location2)),
                       name=f'Location 2')

title = pn.pane.HTML('<h2>Solactus Alpha</h2>')
text = pn.pane.HTML('<h4>Input city, address, or coordinates.<br><br>'
                    'Created in Python with: '
                    'numpy and pandas for wrangling data; '
                    'geopy and skyfield for computing sunset '
                    'times at input locations; '
                    'holoviews, bokeh, hvplot, and panel '
                    'for interactive plots; and '
                    'Jupyter notebook for rapid development.'
                    '</h4>'
                    )
widget1 = pn.interact(trigger, Location1='Champaign, IL')
widget2 = pn.interact(trigger, Location2='Shanghai, China')

panel = pn.Column(title, text,
                  pn.Row(widget1[0],
                         widget2[0]),
                  pn.Tabs(widget1[1],
                          widget2[1]))

panel.server_doc()