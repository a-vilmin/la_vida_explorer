import pandas.io.sql as psql
import sqlite3 as sql
import json
from os.path import join, dirname
import pandas as pd
import numpy as np
from collections import defaultdict

from bokeh.plotting import figure
from bokeh.layouts import layout, widgetbox
from bokeh.models import ColumnDataSource, HoverTool, Div, TapTool, \
    CustomJS
from bokeh.models.widgets import Slider, CheckboxGroup, TextInput, DataTable, \
    TableColumn, Button
from bokeh.io import curdoc
from bokeh.sampledata import us_states


conn = sql.connect(join(dirname(__file__), "BaseballKnowledge.db"))
query1 = open(join(dirname(__file__), 'query1.sql')).read()
pitchers = psql.read_sql(query1, conn)
query2 = open(join(dirname(__file__), 'query2.sql')).read()
batters = psql.read_sql(query2, conn)
players = pd.merge(batters, pitchers, how='outer',
                   on=['nameFirst', 'nameLast', 'year_id', 'team',
                       'birthCountry'])


players.replace(to_replace=["NULL", np.NaN], value=0, inplace=True)
players['batter_war'] = pd.to_numeric(players['batter_war'])

team_data = json.load(open(join(dirname(__file__), 'stadium.json')))

desc = Div(text=open(join(dirname(__file__), "description.html")).read(),
           width=800)
# Create Input controls

min_year = Slider(title="Start Year", start=1900,
                  end=2017, value=1970, step=1)
max_year = Slider(title="End Year", start=1900, end=2017, value=2014, step=1)
search_player = TextInput(value=None, title="Player Search")
clear_button = Button(label="Clear Search", button_type="success")
country_select = CheckboxGroup(labels=["P.R.", "D.R.", "Cuba", "Venezuela",
                                       "Mexico", "Panama", "Colombia",
                                       "Nicaragua", "Brazil", "Curacao"],
                               active=[0])

# Create Column Data Source that will be used by the plot
source = ColumnDataSource(data=dict(x=[], y=[], color=[], war=[],
                                    team=[], size=[]))

p = figure(plot_height=600, plot_width=1200,
           title="", toolbar_location=None)

us_map = us_states.data.copy()

del us_map["HI"]
del us_map["AK"]

# separate latitude and longitude points for the borders
#   of the states.
state_xs = [us_map[code]["lons"] for code in us_map]
state_ys = [us_map[code]["lats"] for code in us_map]
# Draw state lines
p.patches(state_xs, state_ys, fill_alpha=0.0,
          line_color="#000000", line_width=1)

# Add circles
circles = p.circle(x="x", y="y", source=source, size="size",
                   color="color", name="team", fill_alpha=.6)

# Add table

table_source = ColumnDataSource(data=dict(name=[], war=[],
                                          team=[], country=[]))
columns = [
    TableColumn(field="team", title="Team"),
    TableColumn(field="name", title="Name"),
    TableColumn(field="war", title="War"),
    TableColumn(field="country", title="Country")
    ]
# TODO fix display issue cutting off bottom (just Chrome?)
data_table = DataTable(source=table_source, columns=columns,
                       width=400, height=450, row_headers=False)


def select_players():
    if search_player.value:
        players['full_name'] = players['nameFirst'] + " " + players['nameLast']
        selected = players.loc[(players['full_name'] ==
                                search_player.value.strip().title())]
    else:
        order = {0: "P.R.", 1: "D.R.", 2: "Cuba", 3: "Venezuela",
                 4: "Mexico", 5: "Panama", 6: "Colombia", 7: "Nicaragua",
                 8: "Brazil", 9: "Curacao"}
        countries = [order[x] for x in country_select.active]

        selected = players.loc[(players['year_id'] >= min_year.value) &
                               (players['year_id'] <= max_year.value) &
                               (players['birthCountry'].isin(countries))]
    return selected


def apply_color(row):
    try:
        return team_data[row['team']]['color']
    except KeyError:
        return "#000000"


def apply_long(row):
    try:
        return team_data[row['team']]['lng']
    except KeyError:
        return np.NaN


def apply_lat(row):
    try:
        return team_data[row['team']]['lat']
    except KeyError:
        return np.NaN


def apply_players(row, selected):
    players = ""
    try:
        for player, war in selected[row['team']].items():
            players += player + ":" + str(war) + ":" + row['team'] + ","
    except KeyError:
        pass
    return players


def update(update_type='default'):
    if update_type == 'default':
        selected = select_players()
    elif update_type == 'clear':
        search_player.value = ''
        selected = select_players()
    elif update_type == 'table_select':
        selected_index = table_source.selected["1d"]["indices"][0]
        name = table_source.data['name'][selected_index].strip().title()
        players['full_name'] = players['nameFirst'] + " " + players['nameLast']
        selected = players.loc[(players['full_name'] == name)]

    # probably move this to select_players so you can do selectors on type
    df = selected.groupby('team', as_index=False)['pitcher_war'].sum()
    df = df.merge(selected.groupby('team', as_index=False)['batter_war']
                  .sum(),
                  how='left', on='team')
    data = pd.DataFrame(columns=['team', 'war', 'long', 'lat',
                                 'color', 'players'])
    data['team'] = df['team']
    data['war'] = df['batter_war'] + df['pitcher_war']
    data['color'] = data.apply(lambda row: apply_color(row), axis=1)
    data['long'] = data.apply(lambda row: apply_long(row), axis=1)
    data['lat'] = data.apply(lambda row: apply_lat(row), axis=1)
    data['size'] = data['war'] + 10

    selected_dict = defaultdict(lambda: defaultdict(float))
    for i, row in selected.iterrows():
        name = (row['nameFirst'] + " " + row['nameLast'] +
                ":" + row['birthCountry'])
        war = row['batter_war'] + row['pitcher_war']
        selected_dict[row['team']][name] += war

    data['players'] = data.apply(lambda row:
                                 apply_players(row, selected_dict), axis=1)

    data = data.dropna()
    source.data = dict(
        x=data['long'],
        y=data['lat'],
        team=data['team'],
        color=data["color"],
        war=data['war'],
        size=data['size'],
        players=data['players']
    )
    if update_type == 'table_select':
        # deselect circles to display player
        source.selected = {'0d': {'glyph': None, 'indices': []},
                           '1d': {'indices': []},
                           '2d': {'indices': {}}}


def update_wrapped(_):
    update()


def update_click_wrapped():
    update('clear')


def open_table_link(event):
    selected_index = table_source.selected["1d"]["indices"][0]
    name = table_source.data['name'][selected_index].strip().title()
    print(name)


click_circle_callback = """
var data = source.data;
var cdata = circle.data;
var index = cb_data.source.selected['1d'].indices[0];
var team_index = source.data['team'].indexOf(cdata.team[index]);

var player_table = {'name': [], 'war': [], 'team': [], 'country': []};
if (team_index != -1) {
    var player_list = source.data['players'][team_index].split(',');
    for (var i = 0; i < player_list.length; i++){
        var player = player_list[i].split(':');
        player_table['name'].push(player[0]);
        player_table['war'].push(parseFloat(player[2]));
        player_table['team'].push(player[3]);
        player_table['country'].push(player[1]);
    }
    player_table['name'].pop();
    player_table['war'].pop();
    player_table['team'].pop();
    player_table['country'].pop();
}
table_source.data = player_table;
"""

controls = [min_year, max_year, search_player]
for control in controls:
    control.on_change('value', lambda attr, old, new: update())
country_select.on_click(update_wrapped)
clear_button.on_click(update_click_wrapped)
controls += [country_select]
controls.insert(3, clear_button)

sizing_mode = 'fixed'  # 'scale_width' also looks nice with this example

# Add Circle tooltips on hover
hover = HoverTool(tooltips=[("Team", "@team"), ("Total", "@war")],
                  renderers=[circles])
click = TapTool(renderers=[circles])
click.callback = CustomJS(args={'source': source,
                                'circle': circles.data_source,
                                'table_source': table_source},
                          code=click_circle_callback)
table_source.on_change('selected',
                       lambda attr, old, new: update('table_select'))
p.add_tools(hover, click)
inputs = widgetbox(*controls, sizing_mode=sizing_mode)

lay_out = layout([
    [desc],
    [inputs, p, data_table]
], sizing_mode=sizing_mode)

update()  # initial load of the data

curdoc().add_root(lay_out)
curdoc().title = "La Vida WAR Visualizer"
