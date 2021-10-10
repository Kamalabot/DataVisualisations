import plotly
import plotly.express as px
import plotly.graph_objects as go
import dash
import pandas as pd
import dash_core_components as dcc
import dash_html_components as html
import dash_bootstrap_components as dbc
from dash.dependencies import Output, Input, State
from dash.exceptions import PreventUpdate
from dash_table import DataTable
pd.options.display.max_columns = None
from plotly.subplots import make_subplots
import warnings
warnings.filterwarnings('ignore')
for p in [plotly, dash, jd, dcc, html, dbc, pd,]:
    print(f'{p.__name__:-<30}v{p.__version__}')
    
try:
    import kaggle

    kaggle.api.authenticate()
    kaggle.api.dataset_download_files('kamaljp/learn-platform-districtengagement', path='./data', unzip=True)
except:
    print('download kaggle auth to ~/.kaggle.json')
    
product = pd.read_csv("/data/district_engagement.csv",index_col=0,parse_dates=['time'])
product_focus = pd.read_csv("/data/product_focus.csv")
id_name = product_focus[['LP_ID','Product_Name']]
product = pd.merge(left=product,right=id_name,left_on='lp_id',right_on='LP_ID',how='left')
product = product[product.lp_id.isin(id_name.LP_ID)]
district_modified = pd.read_csv('/data/district_modified.csv')
product = product[product.district.isin(district_modified.district_id)]
product = pd.merge(left=product,right=district_modified[['state','district_id']],left_on='district',
                   right_on='district_id',how='left')
product.drop(['LP_ID','district_id'],inplace=True,axis=1)
product.time = product.time.apply(lambda x : pd.to_datetime(x,format='%Y-%m-%d'))

    
    
learnpf=  dash.Dash(__name__, external_stylesheets=[dbc.themes.COSMO])

def make_empty_fig():
    fig = go.Figure()
    fig.layout.paper_bgcolor = '#E5ECF6'
    fig.layout.plot_bgcolor = '#E5ECF6'
    return fig

learnpf.layout = html.Div([
    
    dbc.Col([
        html.H1('Product Access & Engagement across USA'),
        html.H2('Learn PF Dataset'),

    ], style={'textAlign': 'center'}),
    html.Br(),
    dbc.Row([
        dbc.Col(lg=1),
        dbc.Col([
            dcc.Dropdown(id='product_dropdown',
                        value='Learning A-Z',
                        options=[{'label': lpid, 'value': str(lpid)}
                                for lpid in product.Product_Name.unique()]),
            dcc.Graph(id='product_chart'),
        ], lg=5),
        dbc.Col([
            dcc.Markdown(id='product_details_md',
                         style={'backgroundColor': '#E5ECF6'}),
            html.Br(),
            dcc.Graph(id='product_histogram'),
        ], lg=5),
    
    ]),
    html.Br(),
    html.H2('State and school district access', style={'textAlign': 'center'}),
    html.Br(),
    dbc.Row([
        dbc.Col(lg=1),
        dbc.Col([
            dbc.Label('State'),
            dcc.Dropdown(id='state_dropdown',
                         placeholder='Select a state',
                         options=[{'label': state, 'value': state}
                                  for state in np.sort(product.state.unique())]),
            html.Br(),
            dcc.Graph(id='State_barchart',
                      figure=make_empty_fig())
        ], md=12, lg=5),
        dbc.Col([
            dbc.Label('School'),
            dcc.Dropdown(id='school_dropdown',
                         placeholder='Select School Districts',
                         options=[{'label': school, 'value': school}
                                  for school in np.sort(product.district.unique())]),
            html.Br(),
            dcc.Graph(id='school_timeseries',
                      figure=make_empty_fig())
        ], md=12, lg=5),
    ]),
],style={'backgroundColor': '#E5ECF6'})

@learnpf.callback(Output('product_chart', 'figure'),
                  Output('product_details_md', 'children'),
                  Output('product_histogram', 'figure'),
                  Input('product_dropdown', 'value'))

def product_chart(lpid):
    lpid_df = product[product.Product_Name == lpid]
    lpid_df.sort_values(by='time',ascending=True,inplace=True)
    lpfig = go.Figure()
    lpfig.add_trace(go.Scatter(x=lpid_df.time,
                              y=lpid_df.engagement_index,
                              mode='lines',
                              line_color='blue',
                              name='engagement_index'))
    lpfig.add_trace(go.Scatter(x=lpid_df.time,
                              y=lpid_df.pct_access,
                              mode='lines',
                              line_color='green',
                              name='Percentage_access'))
    
    lp_hist = lpid_df.groupby('state').lp_id.count().reset_index().sort_values(by='lp_id',ascending = False)[:10]
    lphist = go.Figure()
    lphist.add_trace(go.Bar(y=lp_hist.state,x=lp_hist.lp_id,orientation='h'))
    lphist.update_layout(title='Which state uses this product?')
    
    if lpid_df.empty:
        markdown = f"""
        ## "Please select the Product to learn about its features, like"
        * **URL of the product**
        * **Sectors it belongs to**
        * **Provider_Company_Name**
        * **Primary_Essential_Function**
        """
    else:
        markdown = f"""
        ## Your Selection : {product_focus[product_focus.Product_Name == lpid].values[0][2]}  
        * **URL of the product** {product_focus[product_focus.Product_Name == lpid].values[0][1]}
        * **Sectors it belongs to** {product_focus[product_focus.Product_Name == lpid].values[0][4]}
        * **Provider_Company_Name** {product_focus[product_focus.Product_Name == lpid].values[0][5]}
        * **Primary_Essential_Function** {product_focus[product_focus.Product_Name == lpid].values[0][8]}
        """
    return lpfig, markdown,lphist

    
@learnpf.callback(Output('State_barchart', 'figure'),
              Input('state_dropdown', 'value'))

def state_chart(state):
    state_df=product[product.state == state]
    state_df.loc[:,'district'] = state_df.district.apply(lambda x: str(x))
    state_fig = px.treemap(state_df, path =[px.Constant("all"),'district','Product_Name'],
                           values='engagement_index',color='district')
    return state_fig
    
@learnpf.callback(Output('school_timeseries', 'figure'),
                  Input('school_dropdown', 'value'))
    
def school_series(school):
    school_df = product[product.district == school]
    school_df.sort_values(by='time',ascending=True,inplace=True)
    grp_school = school_df.groupby('time')['pct_access','engagement_index'].sum().reset_index()
    school_fig = px.line(grp_school,x='time',y='engagement_index')
    return school_fig
    
learnpf.run_server(mode='external', height=1200, port=1234)
