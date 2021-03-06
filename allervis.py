import dash
import dash_core_components as dcc
import dash_bootstrap_components as dbc
import dash_html_components as html
from dash.dependencies import Input, Output, State, ClientsideFunction

import plotly.express as px
import plotly.graph_objects as go

import pandas as pd
import numpy as np
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import MinMaxScaler

# ------------------------------------------------------------------------------
# Data handling

data_path = 'Food Allergies Data'
allergen_paths = {
    'Beef': f'{data_path}//beef-and-buffalo-meat-consumption-per-person.csv',
    'Seafood': f'{data_path}//fish-and-seafood-consumption-per-capita.csv',
    'Egg': f'{data_path}//per-capita-egg-consumption-kilograms-per-year.csv',
    'Milk': f'{data_path}//per-capita-milk-consumption.csv',

    # nuts:
    'Peanut': f'{data_path}//per-capita-peanut-consumption.csv',
    'Almond': f'{data_path}//almond-consumption-per-capita.csv',
    'Cashew': f'{data_path}//cashew-consumption-per-capita.csv',
    'Hazelnut': f'{data_path}//hazelnuts-consumption-per-capita.csv',
    'Macadamia': f'{data_path}//macadamia-consumption-per-capita.csv',
    'Pecan': f'{data_path}//pecans-consumption-per-capita.csv',
    'Pine': f'{data_path}//pine-nuts-consumption-per-capita.csv',
    'Pistachio': f'{data_path}//pistachios-consumption-per-capita.csv',
    'Walnut': f'{data_path}//walnuts-consumption-per-capita.csv',

    # cereals:
    'Barley': f'{data_path}//barley-consumption-per-capita.csv',
    'Corn': f'{data_path}//corn-maize-consumption-per-capita.csv',
    'Oat': f'{data_path}//oats-consumption-per-capita.csv',
    'Rice': f'{data_path}//rice-consumption-per-capita.csv',
    'Rye': f'{data_path}//rye-consumption-per-capita.csv',
    'Wheat': f'{data_path}//wheat-consumption-per-capita.csv',

}

nuts = ['Peanut', 'Almond', 'Cashew', 'Hazelnut', 'Macadamia', 'Pecan', 'Pine', 'Pistachio', 'Walnut']

list_of_allergens = sorted(list(allergen_paths.keys()))
list_of_common_allergens = sorted(['Milk', 'Egg', 'Seafood', 'Peanut', 'Wheat'])
# ---------------------------------------------------
preprocess = False

# missing_countries_df = pd.read_csv(f'{data_path}//countries_to_add.csv')

if preprocess:
    allergen_data = {}
    for allergen, path in allergen_paths.items():
        df = pd.read_csv(path)
        allergen_data[allergen] = df

    # retrieving the most recent year data for each country
    all_dfs_most_recent_values = {}

    for allergen in allergen_data.keys():
        df = allergen_data[allergen]
        most_recent_year = df['Year'].iloc[-1]

        df_most_recent_values = df.groupby(['Code', 'Entity']).apply(lambda x: pd.Series(
            {allergen: x[df.columns[-1]].iloc[-1]}))

        all_dfs_most_recent_values[allergen] = df_most_recent_values

    # concatenating all allergens into one df
    concatenated = pd.concat(all_dfs_most_recent_values.values(), axis=1)

    # imputing the missing data with the given strategy
    imputer_median = SimpleImputer(missing_values=np.nan, strategy='median')
    scaler = MinMaxScaler()

    for column in concatenated.columns:
        if column not in nuts:
            concatenated[column] = imputer_median.fit_transform(np.array(concatenated[column]).reshape(-1, 1))
        else:
            min_col = concatenated[column].min()
            imputer_min = SimpleImputer(missing_values=np.nan, strategy='constant', fill_value=min_col)
            concatenated[column] = imputer_min.fit_transform(np.array(concatenated[column]).reshape(-1, 1))

        max_col = concatenated[column].max()
        concatenated[column] /= max_col

    concatenated = concatenated.reset_index()

    # adding continent info
    continents = pd.read_csv(f'{data_path}//continents.csv', keep_default_na=False)
    continents['Continent'].replace({'NA': 'NAM'}, inplace=True)

    concatenated = concatenated.merge(continents, how='left', left_on='Code', right_on='alpha3').drop(
        columns=['alpha2', 'alpha3', 'numeric', 'fips', 'Country', 'Capital', 'Area in km²'])

    concatenated.to_csv(f'{data_path}//concatenated.csv', index=False)
# ------------------------------------------------------------------------------

concatenated = pd.read_csv(f'{data_path}//concatenated.csv')

app = dash.Dash()
server = app.server

# -------------------------------------------------------------------------------

allergen_options = [{"label": str(allergen), "value": str(allergen)} for allergen in list_of_allergens]

app.layout = html.Div([
    html.Div([
        html.Div([
            # html.P("AllerVis", className="control_label"),
            "AllerVis | ",
            html.Div(
                dbc.Button(
                    "Help", id="popover-target"
                ),
                style={'display': 'inline-block', 'font-size': '25px',
                       'margin-bottom': '2px',
                       "font-family": "Helvetica"
                       },

            )
        ],
            style={'margin': '2px 5px', 'padding': '2px 10px', 'font-size': '25px', 'text-align': 'left',
                   "font-family": "Helvetica", "font-weight": "bold",
                   # "background-color": "#f9f9f9",
                   'background-image': 'linear-gradient(to left, rgba(64, 78, 119,0), rgba(64, 78, 119,5))',
                   'color': 'white'
                   }
        ),

        dbc.Popover(
            [
                dbc.PopoverHeader("Instructions:"),
                dbc.PopoverBody(" - Single click on a legend item to exclude"),
                dbc.PopoverBody(" - Double click on a legend item to isolate"),
                dbc.PopoverBody(" - Use drag and scroll to change the view of the map"),
                dbc.PopoverBody(" - Double click anywhere to reset the view"),
                dbc.PopoverHeader("Information: "),
                dbc.PopoverBody(" - Choropleth: color encodes aggregated prevalence (saturation)/category "
                                "of the least or most prevalent allergen (hue)"),
                dbc.PopoverBody(" - Bubble map: size encodes aggregated prevalence"),
                dbc.PopoverBody(" - Bubble map: color encodes aggregated prevalence (saturation)/category "
                                "of the least or most prevalent allergen (hue)"),
            ],
            id="popover",
            is_open=False,
            target="popover-target",
            placement='bottom-start',
            style={"background-color": "rgba(0, 0, 0, 0.8)",
                   'font-size': '15px', 'color': 'white',
                   'margin': '5px', 'padding': '0px 5px 5px 5px',
                   "font-family": "Segoe UI", 'border-radius': '6px'
                   }

        ),

        html.Div(
            [
                html.Div([
                    html.Div([
                        html.P("Filter by allergen:", className="control_label"),
                    ],
                        style={'width': '30%', 'height': '2px', 'display': 'inline-block'}
                    ),

                    html.Div([
                        dcc.RadioItems(
                            id="allergen_selector",
                            options=[
                                {"label": "Common ", "value": "common"},
                                {"label": "Custom ", "value": "custom"},
                                {"label": "All ", "value": "all"},
                            ],
                            value="common",
                            labelStyle={"display": "inline-block"},
                            className="dcc_control",
                        ),
                    ],
                        style={'margin': '5px', 'display': 'inline-block'}
                    ),
                ],
                    style={'margin': '5px'}),

                dcc.Dropdown(
                    id="allergens",
                    options=allergen_options,
                    multi=True,
                    value=list_of_allergens,
                    className="dcc_control",
                ),
                html.Div([
                    html.Div([
                        html.P("Filter by region:", className="control_label"),
                    ],
                        style={'width': '30%', 'height': '2px', 'display': 'inline-block'}
                    ),
                    html.Div([
                        dcc.Dropdown(
                            id="regions",
                            options=[{"label": "World ", "value": "world"},
                                     {"label": "Europe ", "value": "europe"},
                                     {"label": "Asia ", "value": "asia"},
                                     {"label": "Africa ", "value": "africa"},
                                     {"label": "North America ", "value": "north america"},
                                     {"label": "South America ", "value": "south america"},
                                     {"label": "Oceania ", "value": "oceania"},

                                     ],
                            multi=False,
                            value='world',
                            className="dcc_control",
                        ),
                    ],
                        style={'margin': '5px', 'width': '200px', 'height': '20px',
                               'font-size': "100%", 'display': 'inline-block'}
                    )
                ]),

                html.Div([
                    html.Div([
                        html.P("Select map idiom:", className="control_label"),
                    ],
                        style={'width': '30%', 'height': '2px', 'display': 'inline-block'}
                    ),

                    html.Div([
                        dcc.RadioItems(
                            id="map_idiom_selector",
                            options=[
                                {"label": "Choropleth ", "value": "choropleth"},
                                {"label": "Bubble map ", "value": "bubble"}
                            ],
                            value="choropleth",
                            labelStyle={"display": "inline-block"},
                            className="dcc_control",
                        ),
                    ],
                        style={'margin': '5px', 'display': 'inline-block'}
                    )
                ]),

                html.P("Select color scheme:", className="control_label"),
                html.Div([
                    dcc.RadioItems(
                        id="color_scheme_selector",
                        options=[
                            {"label": "Sequential ", "value": "sequential"},
                            {"label": "Most Prevalent ", "value": "mpa"},
                            {"label": "Least Prevalent ", "value": "lpa"},
                        ],
                        value="mpa",
                        labelStyle={"display": "inline-block"},
                        className="dcc_control",
                    ),
                ],
                    style={'margin': '5px'}),

            ],
            className="pretty_container",
            id="cross-filter-options",
            style={"width": "38%", "padding": 10, "margin": "5px", "background-color": "#f9f9f9",
                   'display': 'inline-block', 'vertical-align': 'top', 'min-height': '355px',
                   'position': 'relative',
                   "box-shadow": "0 4px 8px 0 rgba(0, 0, 0, 0.05), 0 6px 20px 0 rgba(0, 0, 0, 0.05)",
                   "font-family": "Helvetica"},
        ),

        html.Div(
            [
                html.Div([
                    dcc.Graph(id="map_graph",
                              config={'modeBarButtonsToRemove': ['select2d', 'lasso2d'],
                                      'displaylogo': False})
                ],
                    id="map_container",
                    className="map_container",
                    style={'margin-top': '20px'}
                ),
            ],
            id="map_area",
            className="map area",
            style={"margin": "5px", "width": "58%", "height": "375px",
                   'display': 'inline-block', 'position': 'relative',
                   "background-color": "#ffffff",
                   "box-shadow": "0 4px 8px 0 rgba(0, 0, 0, 0.05), 0 6px 20px 0 rgba(0, 0, 0, 0.05)"}
        ),

        html.Div(
            [
                html.Div(
                    [dcc.Graph(id="stack_barchart_graph",
                               config={'modeBarButtonsToRemove': ['lasso2d'],
                                       'displaylogo': False})],
                    id="stack_barchart_container",
                    className="pretty_container",
                ),
            ],
            id="stack_barchart_area",
            className="stack barchart area",
            style={"margin": "5px",
                   "box-shadow": "0 4px 8px 0 rgba(0, 0, 0, 0.05), 0 6px 20px 0 rgba(0, 0, 0, 0.05)",
                   }
        ),
    ],
        className="flex-display",
    ),

],
    id="mainContainer",
    style={"padding": '10px', "background-color": "#f2f2f2"},
)


# Radio -> multi
@app.callback(
    Output("allergens", "value"),
    [Input("allergen_selector", "value")]
)
def display_status(selector):
    if selector == "all":
        return list_of_allergens
    elif selector == "common":
        return list_of_common_allergens
    return []


# -------------------------------------------------------------------------------------------
# Graph
@app.callback(
    Output("stack_barchart_graph", "figure"),
    [Input("allergens", "value"), Input("regions", "value")]
)
def update_plot(selected_allergens, selected_region):
    selected_allergens.sort()
    ascending = True

    concatenated['selected_set'] = concatenated.apply(lambda row: row[selected_allergens].sum(), axis=1)
    concatenated.sort_values('selected_set', ascending=ascending, inplace=True)

    region_concatenated = concatenated
    showticklabels = True

    if selected_region == 'world':
        region_concatenated = concatenated
        showticklabels = False
    elif selected_region == 'europe':
        region_concatenated = concatenated[concatenated['Continent'] == 'EU']
    elif selected_region == 'asia':
        region_concatenated = concatenated[concatenated['Continent'] == 'AS']
    elif selected_region == 'africa':
        region_concatenated = concatenated[concatenated['Continent'] == 'AF']
    elif selected_region == 'north america':
        region_concatenated = concatenated[concatenated['Continent'] == "NAM"]
    elif selected_region == 'south america':
        region_concatenated = concatenated[concatenated['Continent'] == 'SA']
    elif selected_region == 'oceania':
        region_concatenated = concatenated[concatenated['Continent'] == 'OC']

    fig = px.bar(region_concatenated, x='Entity', y=selected_allergens, orientation='v', height=400,
                 labels={'variable': 'Allergen',
                         'Entity': 'Country',
                         },
                 # template='plotly_white'
                 title='Aggregated Prevalence'
                 )

    fig.update_layout(
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        ),
        margin=dict(
            l=10,
            r=10,
            b=20,
            t=20,
            pad=4
        ),
        xaxis=dict(
            showticklabels=showticklabels
        ),
    )

    fig.update_yaxes(title=None)
    fig.update_xaxes(title=None)

    return fig


# -------------------------------------------------------------------------------------

@app.callback(
    Output("map_graph", "figure"),
    [Input("allergens", "value"),
     Input("regions", "value"),
     Input("map_idiom_selector", "value"),
     Input("color_scheme_selector", "value")
     ]
)
def update_plot(selected_allergens, selected_region, map_idiom, color_scheme):
    concatenated['selected_set'] = concatenated.apply(lambda row: row[selected_allergens].sum(), axis=1)
    concatenated['most_prevalent_allergen'] = concatenated.apply(
        lambda row: row[selected_allergens][row[selected_allergens] == row[selected_allergens].max()].index[0],
        axis=1)
    concatenated['least_prevalent_allergen'] = concatenated.apply(
        lambda row: row[selected_allergens][row[selected_allergens] == row[selected_allergens].min()].index[0],
        axis=1)

    color = 'selected_set'
    color_continuous_scale = px.colors.sequential.Blues
    color_continuous_midpoint = concatenated['selected_set'].mean()

    if color_scheme == 'sequential':
        color_continuous_scale = px.colors.sequential.Blues

    elif color_scheme == 'mpa':
        concatenated.sort_values(['most_prevalent_allergen'], inplace=True)
        color = 'most_prevalent_allergen'

    elif color_scheme == 'lpa':

        concatenated.sort_values(['least_prevalent_allergen'], inplace=True)
        color = 'least_prevalent_allergen'

    fig = 0

    if selected_region == 'oceania':
        scope = 'world'
    else:
        scope = selected_region

    if map_idiom == 'choropleth':
        fig = px.choropleth(data_frame=concatenated,
                            locations='Code',
                            scope=scope,
                            color=color,
                            hover_name="Entity",  # column to add to hover information
                            color_continuous_scale=color_continuous_scale,
                            # color_continuous_midpoint=color_continuous_midpoint,
                            labels={'selected_set': 'Prevalence',
                                    'most_prevalent_allergen': 'Most Prevalent Allergen',
                                    'least_prevalent_allergen': 'Least Prevalent Allergen',
                                    },
                            title=None,
                            height=340,
                            # hover_data=selected_allergens # Removing due to current lag
                            )
        fig.update_layout(
            margin=dict(
                l=10,
                r=10,
                b=0,
                t=0,
                pad=4
            ),
            geo=dict(
                landcolor='lightgray',
                showland=True,
                showcountries=True,
                countrycolor='gray',
                countrywidth=0.5,
                projection=dict(type='natural earth')
            )
        )

        if selected_region == 'world':
            fig.update_geos(visible=False)

        if selected_region == 'oceania':
            fig.update_geos(visible=False, center=dict(lon=130, lat=-30), projection_scale=3)

    elif map_idiom == 'bubble':

        fig = px.scatter_geo(concatenated,
                             locations='Code',
                             scope=scope,
                             color=color,
                             size='selected_set',
                             hover_name="Entity",  # column to add to hover information
                             color_continuous_scale=color_continuous_scale,
                             labels={'selected_set': 'Prevalence',
                                     'most_prevalent_allergen': 'Most Prevalent Allergen',
                                     'least_prevalent_allergen': 'Least Prevalent Allergen'},
                             title=None,
                             height=340
                             )

        fig.update_layout(
            margin=dict(
                l=5,
                r=5,
                b=0,
                t=0,
                pad=4
            ),
            geo=dict(
                landcolor='lightgray',
                showland=True,
                showcountries=True,
                countrycolor='gray',
                countrywidth=0.5,
                projection=dict(type='natural earth')
            )
        )

        if selected_region == 'oceania':
            fig.update_geos(center=dict(lon=130, lat=-30),
                            projection_scale=3)

        # fig.update_config({'modeBarButtonsToRemove': ['lasso2d']})
    return fig


# ------------------------------------------------------------------------

@app.callback(
    Output("popover", "is_open"),
    [Input("popover-target", "n_clicks")],
    [State("popover", "is_open")],
)
def toggle_popover(n, is_open):
    if n:
        return not is_open
    return is_open

# ---------------------------------------------------------------------------------------


if __name__ == '__main__':
    app.run_server()
