import altair as alt
# import streamlit as st
import pandas as pd
# from sklearn.linear_model import LinearRegression
# from sklearn.model_selection import train_test_split
import numpy as np
from vega_datasets import data
import streamlit as st
from sklearn.linear_model import LinearRegression

alt.data_transformers.disable_max_rows()
st.set_page_config(page_title="Energy, Climate Change, and Global Responsibility", layout="wide", page_icon="💡")

# For reducing the width of the sidebar (Source: https://discuss.streamlit.io/t/change-width-of-sidebar/5339/4)
st.markdown(
    """
    <style>
    [data-testid="stSidebar"][aria-expanded="true"] > div:first-child {
        width: 280px;
    }
    [data-testid="stSidebar"][aria-expanded="false"] > div:first-child {
        width: 280px;
        margin-left: -280px;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

@st.cache
def get_energy(with_coords=True):

    energy_sources = pd.read_csv('./data/primary-energy-source-bar.csv')

    energy_sources = energy_sources.sort_values(['Entity', 'Year'])

    for entity in energy_sources.Entity.unique():
        indices = energy_sources.Entity == entity
        for col in energy_sources.columns:
            if col != 'Entity' and col != 'Code' and col != 'Year' and col != 'TotalEnergy':
                temp = energy_sources[indices][col]
                temp = temp.fillna('ffill')
                energy_sources.loc[indices, col] = temp

    energy_sources = energy_sources[energy_sources.Year == 2019].copy()
    energy_sources['TotalEnergy'] = 0
    for col in energy_sources.columns:
        if col != 'Entity' and col != 'Code' and col != 'Year' and col != 'TotalEnergy':
            energy_sources['TotalEnergy'] += energy_sources[col]
    
    energy_sources['Entity'] = energy_sources.Entity.astype('str')
    
    energy_sources.loc[(energy_sources.Entity == 'United States'), ['Entity']] = 'United States of America'
    if with_coords == False:
        return energy_sources
    lats = pd.read_csv('./data/average-latitude-longitude-countries.csv')
    
    lats.loc[(lats.Country == 'United States'), ['Country']] = 'United States of America'

    energy_sources = energy_sources[energy_sources.Entity != 'Europe']
    country_lat = energy_sources.merge(lats, left_on='Entity', right_on='Country')
    return country_lat

@st.cache
def get_energypc(with_coords=True):
    population = pd.read_csv('./data/population-past-future.csv')
    population = population[~population.Code.isnull()]
    population = population[population.Code != 'NaN']
    population = population.sort_values(by=['Entity', 'Year'])
    for entity in population.Entity.unique():
        indices = population.Entity == entity
        temp = population[indices]['Population (historical estimates and future projections)']
        temp = temp.fillna('ffill')
        population.loc[indices, 'Population (historical estimates and future projections)'] = temp

    population = population[population.Year == 2019]
    population['Entity'] = population.Entity.astype('str')
    population = population[population.Entity != 'Europe']
    population.loc[(population.Entity == 'United States'), ['Entity']] = 'United States of America'
    

    df = get_energy(with_coords)
    joined = population.merge(df, on='Entity')
    joined['EnergyPerCapita'] = joined['TotalEnergy']/joined['Population (historical estimates and future projections)']
    if with_coords:
        joined['Latitude_x'] = joined['Latitude']
        joined['Longitude_x'] = joined['Longitude']
    return joined

@st.cache
def get_fuelco2():
    fuel_co2 = pd.read_csv('./data/co2-emissions-by-fuel-line.csv')
    fuel_co2 = fuel_co2[(fuel_co2.Year == 2019)]
    co2_cols = ['Annual CO2 emissions from oil', 'Annual CO2 emissions from flaring', 'Annual CO2 emissions from cement', 'Annual CO2 emissions from coal', 'Annual CO2 emissions from gas', 'Annual CO2 emissions from other industry']
    co2_rename = ['Oil', 'Flaring', 'Cement', 'Coal', 'Gas', 'Other Industries']
    fuel_co2.loc[(fuel_co2.Entity == 'United States'), ['Entity']] = 'United States of America'
    fuel_co2 = fuel_co2.rename(index=str, columns=dict(zip(co2_cols, co2_rename)))
    fuel_co2['NetCO2'] = 0
    for col in co2_rename:
        fuel_co2[col] = fuel_co2[col].fillna(0)
        fuel_co2['NetCO2'] += fuel_co2[col]
    
    co2_cols = co2_rename
    population = pd.read_csv('./data/population-past-future.csv')
    
    population.loc[(population.Entity == 'United States'), ['Entity']] = 'United States of America'
    population = population[~population.Code.isnull()]
    population = population[population.Code != 'NaN']
    population = population[population.Year == 2019]
    population['Entity'] = population.Entity.astype('str')
    population = population[population.Entity != 'Europe']

    fuel_co2['Entity'] = fuel_co2.Entity.astype('str')
    co2_pc = population.merge(fuel_co2, on='Entity')
    co2_pc['NetCO2_PC'] = co2_pc['NetCO2']/co2_pc['Population (historical estimates and future projections)']
    for col in co2_cols:
        co2_pc[col + '_PC'] = co2_pc[col]/co2_pc['Population (historical estimates and future projections)']
    # co2_pc.head()

    world_population = 7713468203
    for col in co2_cols+['NetCO2']:
        co2_pc[col] = co2_pc[col+'_PC']*world_population
    return co2_pc, co2_cols

# @st.cache
def get_energy_charts_circle():
    url = 'https://cdn.jsdelivr.net/npm/world-atlas@2/countries-110m.json'
    selector = alt.selection_single(name="selector", fields=['Entity'])
    countries = alt.topo_feature(data.world_110m.url, 'countries')
    geo = alt.Chart(countries).mark_geoshape(
        fill='lightblue',
        stroke='white').properties(
        width=580,
        height=500
    )
    country_lat = get_energy()

    color_range = alt.Color('TotalEnergy:Q', 
                        scale=alt.Scale(
                            type='pow', exponent=0.6,
    #                         domain=(temp_min, temp_max), 
                            range=['yellow', 'orange', 'red']
                        ))
    circles = alt.Chart(country_lat).mark_circle().encode(
        latitude='Latitude:Q',
        longitude="Longitude:Q",
        size=alt.Size("TotalEnergy:Q", scale=alt.Scale(range=[0, 3000]), legend=None),
        tooltip=['Entity'],
        color=alt.condition(selector, color_range, alt.value('lightgreen'))
    ).add_selection(selector)

    g1 = geo+circles

    joined_lats = get_energypc()

    countries = alt.topo_feature(url, 'countries')
    geo2 = alt.Chart(countries).mark_geoshape(
            fill='lightblue',
            stroke='white'
        ).properties(
            width=580,
            height=500
    ).project(
        clipExtent= [[0, 0], [580, 360]]
    )
    color_range2 = alt.Color('EnergyPerCapita:Q', 
                        scale=alt.Scale(
                            type='pow', exponent=0.6,
    #                         domain=(temp_min, temp_max), 
                            range=['yellow', 'orange', 'red']
                        )
                    )
    circles2 = alt.Chart(joined_lats).mark_circle().encode(
        latitude='Latitude:Q',
        longitude="Longitude:Q",
        size=alt.Size("EnergyPerCapita:Q", scale=alt.Scale(range=[0, 1000]), legend=None),
        tooltip=['Entity', 'EnergyPerCapita:Q'],
        color=alt.condition(selector, color_range2, alt.value('lightgreen'))
        
    ).add_selection(selector)

    g2 = (geo2+circles2)

    return (g1&g2).resolve_scale(color='independent'), selector
    # return g2, selector


# @st.cache
def get_energypc_chart_heatmap():
    url = 'https://cdn.jsdelivr.net/npm/world-atlas@2/countries-110m.json'
    selector = alt.selection_single(name="selector", fields=['Entity'])
    countries = alt.topo_feature(url, 'countries')
    energy_sources = get_energy(with_coords=False)
    color_range = alt.Color('TotalEnergy:Q', 
                       scale=alt.Scale(
                        type='pow', exponent=0.6, 
                        range=['lightblue', 'yellow', 'orange', 'red']
                    ))
    base_chart = alt.Chart(countries,
        title='Net Energy Consumption by Country (TWh)'
    ).mark_geoshape(stroke='white').encode(
        color=alt.condition(selector, color_range, 
                    alt.value('lightgray')
        ),
        # color = color_range,
        tooltip = [alt.Tooltip('properties.name:N', title='Country'), alt.Tooltip('TotalEnergy:Q', title='Total Energy Consumed (TWh)')]
    ).transform_lookup(
        lookup='properties.name',
        from_=alt.LookupData(energy_sources, 'Entity', ['TotalEnergy', 'Country', 'Entity'])
    ).properties(
        width=580,
        height=500
    ).add_selection(selector)

    energy_pc = get_energypc(with_coords=False)
    pc_chart = alt.Chart(countries,
        title='Per Capita Energy Consumption by Country (TWh/person)'
    ).mark_geoshape(stroke='white').encode(
        color=alt.condition(selector, alt.Color('EnergyPerCapita:Q', 
                       scale=alt.Scale(
                        type='pow', exponent=0.6, 
                        range=['lightblue', 'yellow', 'orange', 'red']
                    )), 
                    alt.value('lightgray')
        ),
        tooltip = [alt.Tooltip('properties.name:N', title='Country'), alt.Tooltip('EnergyPerCapita:Q', title='Per Capita Energy Consumed (TWh/person)')]
    ).transform_lookup(
        lookup='properties.name',
        from_=alt.LookupData(energy_pc, 'Entity', ['EnergyPerCapita', 'Country', 'Entity'])
    ).properties(
        width=580,
        height=500
    ).add_selection(selector)

    # return (base_chart|pc_chart).resolve_scale(color='independent'), selector
    return base_chart, pc_chart, selector

# Credit: https://stackoverflow.com/questions/67997825/python-altair-generate-a-table-on-selection
def get_chart_table(data):
    ranked_text = alt.Chart(data).mark_text(align='right').encode(
    y=alt.Y('row_number:O',axis=None)
    ).transform_window(
        row_number='row_number()'
    ).transform_filter(
        'datum.row_number < 10'
    )

    country = ranked_text.encode(text='Entity:N', strokeWidth=alt.value(0)).properties(title=alt.TitleParams(text='Country', align='right'))
    energy = ranked_text.encode(text='TotalEnergy:N', strokeWidth=alt.value(0)).properties(title=alt.TitleParams(text='Total Energy Consumption (TWh)', align='right'))
    text = alt.hconcat(country, energy)
    return text


def per_capita_energy():
    


    st.markdown("""
    ## Energy Consumption and CO2 Emissions
    Energy production is the major driving force behind climate change. Energy production is driven by energy needs which can vary by country. The geomap has been overlayed by the net energy consumption of that country in the year 2019. It can be seen that countries like China, Russia, India, and USA have a very high energy consumption rate.
    However, net energy consumption does not tell the full story. Some countries have more habitable regions and might have more people living on the same net energy. Click on the `Show Per Capita Energy` checkbox to find the per capita energy consumption by country.

    The worst offenders are very different if we look at it from the per capita energy perspective. Countries like UAE, USA, Saudi Arabia, and Iceland have a very high per capita energy consumption. However, it must be noted that these countries have a much higher standard of living when compared to countries like Algeria and India. 

    If we are expecting these countries to grow, the per capita energy needs of these countries will also grow and so will the net CO2 emissions. Let's try visualize the hypothetical scenario of every country in the world has the same standard of living as the developed countries. Try clicking on one of the countries on the world map. It's per capita energy consumption and current fuel mix will be applied to all the countries and the resulting effects can be seen on the charts below.
    """)
    geo_map1, geo_map2, selector = get_energypc_chart_heatmap()

    per_capita = st.checkbox("Show Per Capita Energy")


    co2_pc, co2_cols = get_fuelco2()
    # co2_pc_world = co2_pc[co2_pc.Entity == 'World']
    # net_world_co2 = co2_pc[co2_pc.Entity == 'World'].NetCO2_WORLD.max()
    co2_pc = co2_pc[co2_pc.Entity != 'World']
    net_world_co2 = co2_pc['NetCO2'].mean()
    net_co2_max = co2_pc['NetCO2'].max() + 10000
    fuel_co2_long_2 = co2_pc.melt(id_vars='Entity', value_vars=list(map(lambda x: x, co2_cols)))

    co2_chart = alt.Chart(
        fuel_co2_long_2,
        title='Global CO2 Emissions by Fuel Type Based on Selected Country\'s Rate'
    ).mark_bar().encode(
        x=alt.X('variable', title='Emissions Source'), 
        y=alt.Y('mean(value):Q', title='CO2 emissions (T)'),
        tooltip = [alt.Tooltip('mean(value):Q', title='CO2 emissions (T)')]
    ).properties(
            width=200,
            height=200
    ).transform_filter(
                selector
    ).add_selection(selector)

    netCO2_Line = pd.DataFrame({
            'CO2 emissions(T)': [net_world_co2],
            'Red Bar indicates:': "Original Net CO2 Emissions"
        })
    netCO2_rule_chart = alt.Chart(netCO2_Line).mark_rule().encode(
        y=alt.Y('CO2 emissions(T):Q', title='CO2 emissions(T)'),
        color = alt.Color('Red Bar indicates:', scale = alt.Scale(range=['red'])),
        tooltip = [alt.Tooltip('CO2 emissions(T):Q', title='Global CO2 emissions(T) (Original)')]
    ).properties(
        width=200,
        height=200
    )

    fuel_co2_long_full = co2_pc.melt(id_vars='Entity', value_vars=['NetCO2'])
    co2_chart_full = alt.Chart(
        fuel_co2_long_full,
        title='Global CO2 Emissions Based on Selected Country\'s Rate'
    ).mark_bar().encode(
        x=alt.X('variable', title='World'), 
        y=alt.Y('mean(value):Q', title='CO2 emissions(T)', scale=alt.Scale(domain=[0, net_co2_max])),
        tooltip = [alt.Tooltip('mean(value):Q', title='CO2 emissions (T)')],
    ).properties(
            width=200,
            height=200
    ).transform_filter(
                selector
    ).add_selection(selector) + netCO2_rule_chart



    df_energy_mix = get_energy(with_coords=False)
    cols = [col for col in df_energy_mix.columns if col not in ('Entity', 'Code', 'Year', 'TotalEnergy')]

    df_melt = df_energy_mix.melt(id_vars='Entity', value_vars=cols)
    energy_mix_chart = alt.Chart(
        df_melt, 
        title="Energy Sources for the Selected Country"
            ).mark_arc().encode(
        theta=alt.Theta(field="value", type="quantitative"),
        color=alt.Color(field="variable", title="Fuel Type"),
        tooltip = [alt.Tooltip('value:Q', title='Energy TWh'), alt.Tooltip('Entity', title='Country'), alt.Tooltip('variable', title='Fuel Type')],
    ).transform_filter(selector).add_selection(selector).properties(width=180, height=180)


    if per_capita:
        st.markdown("""### What if every country had the same consumption rate?
            Click on a country to apply its consumption rate to the world.
        """)
        st.write(((geo_map1 | geo_map2).resolve_scale(color='independent') & (energy_mix_chart | co2_chart | co2_chart_full).resolve_scale(color='independent')).resolve_scale(color='independent'))
    else:
        table_df = df_energy_mix[['Entity', 'TotalEnergy']].sort_values(['TotalEnergy'], ascending=False)
        table_df = table_df[~table_df.Entity.isin(('World', 'Asia Pacific', 'OECD', 'Non-OECD', 'European Union', 'Middle East', 'Africa', 'South & Central America', 'North America', 'Europe', 'CIS'))]
        st.write((geo_map1 | get_chart_table(table_df)).resolve_scale(
            color="independent").configure_view(strokeWidth=0))

def energy_forecast():
    st.markdown("""

    ### Predicting energy production and demand based on current growth rate

    """)
    
    st.write("The goal of this predictive modeling is to identify countries who have not been able to meet their electricity demand with their electricity generation, to identify opportunities of excess electricity generation, and to do efficient energy planning for the upcoming years. We also perform an analysis to check the electricity generated using fossil fuels and renewable sources of energy.")



    def load_data():
        energy_data = pd.read_csv("./data/owid-energy-data.csv")
        return energy_data.sort_index()

    energy_data = load_data()
    all_countries = list(set(energy_data["country"]))

    all_countries.sort()
    option = st.selectbox(
        'Select a Region:',
        all_countries)

    energy_ukr = energy_data[energy_data['country']==option]

    energy_ukr = energy_ukr.dropna(subset = ['electricity_demand'])

    try:

        x_years = list(energy_ukr['year']) + list(range(2023,2030))



        #   st.write("Electricity Demand Historic Data and Prediction")
        X = energy_ukr['year'].values[:,np.newaxis]
        y_demand= energy_ukr['electricity_demand']

        model = LinearRegression()
        model.fit(X, y_demand)

        #st.write(model.predict(x_years))
        object_for_visualization = {'Years':x_years, "Power(in Terawatt-hour)": list(y_demand) + list(model.predict(np.asarray(x_years[-7:]).reshape(-1,1)))}
        viz_df = pd.DataFrame(object_for_visualization)
        viz_df['date'] = pd.to_datetime(viz_df['Years'])

        chart=alt.Chart(viz_df).mark_point(color = "blue",).encode(
                alt.X("Years", scale=alt.Scale(zero=False)),
                alt.Y("Power(in Terawatt-hour)",  scale=alt.Scale(zero=False)),
                tooltip=["Years", "Power(in Terawatt-hour)"],
                
            ).properties(
                width=800, height=400
            )

        final_chart = chart + chart.transform_regression("Years", "Power(in Terawatt-hour)").mark_line(color = "blue").encode(       
            tooltip=["Years", "Power(in Terawatt-hour)"],
            ).transform_fold(
            ["electricity demand"], 
            as_=["Regression_demand", "y"]
        ).encode(alt.Color("Regression_demand:N"))

        st.markdown("**Electricity Demand and Generation Historic Data and Prediction**")
        st.markdown("In the plot below, the points marked upto 2022 are actual historical values and the lines are the predictions for electricity demand and generation.")

        X = energy_ukr['year'].values[:,np.newaxis]
        y_generation = energy_ukr['electricity_generation']

        model_generation = LinearRegression()
        model_generation.fit(X, y_generation)


        object_for_visualization = {'Years':x_years, "Power(in Terawatt-hour)": list(y_generation) + list(model_generation.predict(np.asarray(x_years[-7:]).reshape(-1,1)))}
        viz_df = pd.DataFrame(object_for_visualization)
        viz_df['date'] = pd.to_datetime(viz_df['Years'])


        chart2=alt.Chart(viz_df).mark_point(color = "red" ).encode(
                alt.X("Years", scale=alt.Scale(zero=False)),
                alt.Y("Power(in Terawatt-hour)",  scale=alt.Scale(zero=False)),
                tooltip=["Years", "Power(in Terawatt-hour)"], 
                
            ).properties(
                width=800, height=400
            )
        final_chart + chart2 + chart2.transform_regression("Years", "Power(in Terawatt-hour)").mark_line().encode(       
            tooltip=["Years", "Power(in Terawatt-hour)"],
            x = alt.X('Years',axis = alt.Axis(format="d")),
            y=alt.Y('Power(in Terawatt-hour)')).transform_fold(
            ["electricity generation"], 
            as_=["Regression_generation", "y"]
        ).encode(alt.Color("Regression_generation:N"))
        st.markdown("**Electricity generation sources: Fossil-fuels vs Renewable Energy**")
        st.markdown("In the plot below, the points marked upto 2022 are actual historical values and the lines are the predictions for electricity generation using fossil fuels and using renewable energy.")

        X = energy_ukr['year'].values[:,np.newaxis]
        y_fossil = energy_ukr['fossil_share_elec']


        model_fossil = LinearRegression()
        model_fossil.fit(X, y_fossil)


        object_for_visualization = {'Years':x_years, "Power(in Terawatt-hour)": list(y_fossil) + list(model_fossil.predict(np.asarray(x_years[-7:]).reshape(-1,1)))}
        viz_df = pd.DataFrame(object_for_visualization)
        viz_df['date'] = pd.to_datetime(viz_df['Years'])


        chart3=alt.Chart(viz_df).mark_point(color = "blue",).encode(
                alt.X("Years", scale=alt.Scale(zero=False)),
                alt.Y("Power(in Terawatt-hour)",  scale=alt.Scale(zero=False)),
                tooltip=["Years", "Power(in Terawatt-hour)"],
                
            ).properties(
                width=800, height=400
            )

        final_chart_2 = chart3 + chart3.transform_regression("Years", "Power(in Terawatt-hour)").mark_line(color = "blue").encode(       
            tooltip=["Years", "Power(in Terawatt-hour)"],
            ).transform_fold(
            ["Fossil fuel electricity share"], 
            as_=["Fossil fuel electricity share", "y"]
        ).encode(alt.Color("Fossil fuel electricity share:N"))


        
        X = energy_ukr['year'].values[:,np.newaxis]
        y_renewables = energy_ukr['renewables_share_elec']


        model_renewable = LinearRegression()
        model_renewable.fit(X, y_renewables)


        object_for_visualization = {'Years':x_years, "Power(in Terawatt-hour)": list(y_renewables) + list(model_renewable.predict(np.asarray(x_years[-7:]).reshape(-1,1)))}
        viz_df = pd.DataFrame(object_for_visualization)
        viz_df['date'] = pd.to_datetime(viz_df['Years'])
        chart4 =alt.Chart(viz_df).mark_point(color = "red" ).encode(
                alt.X("Years", scale=alt.Scale(zero=False)),
                alt.Y("Power(in Terawatt-hour)",  scale=alt.Scale(zero=False)),
                tooltip=["Years", "Power(in Terawatt-hour)"], 
                
            ).properties(
                width=800, height=400
            )
        final_chart_2 + chart4 + chart4.transform_regression("Years", "Power(in Terawatt-hour)").mark_line().encode(       
            tooltip=["Years", "Power(in Terawatt-hour)"],
            x = alt.X('Years',axis = alt.Axis(format="d")),
            y=alt.Y('Power(in Terawatt-hour)')).transform_fold(
            ["Renewable electricity share"], 
            as_=["Renewable electricity share", "y"]
        ).encode(alt.Color("Renewable electricity share:N"))

        #   st.write("Note: The above plot does not consider electricity generated using other sources like oil, gas and others.")

    except Exception as e:
        print(e)
        st.write("Not enough data for this country!")

@st.cache
def get_dataset1():
    return pd.read_csv("./data/Dataset1_cleaned_2.csv").dropna()

@st.cache
def get_emissions():
    return pd.read_csv("./data/emissions_cleaned.csv").dropna()

def climate_change_impact():
    data = get_dataset1()

    data2 = get_emissions()


    st.markdown("""## Climate Hazards of Each country and the Adaptation Action""")
    brush = alt.selection(type='interval')
    selector = alt.selection_single(empty='all', fields=['Country'])

    st.markdown("""Select plots on the graph to see the climate hazards occuring in the following countries""")


    points_climateChange = alt.Chart(
            data,
            title='Disasters by Country and Population'
        ).mark_point().encode(
        x='Climate hazard:N',
        y='Population:Q',
        color=alt.condition(brush, 'Country:N', alt.value('lightgray'))
    ).add_selection(
        brush
    )

    st.markdown("""Select the Country to view the adaptation action implemented""")

    bars_climateChange= alt.Chart(
        data,
        title='Number of Disasters by Country'
    ).mark_bar().encode(
        y='Country:N',
        color='Country:N',
        x=alt.X('count(Country):Q', title='Number of Disasters')
    ).transform_filter(
        brush
    ).add_selection(selector)

    bars_climateChange2 = alt.Chart(
        data,
        title='Adaptation Action by Country and Population'
    ).mark_bar().encode(
        y='Country:N',
        color='Country:N',
        x=alt.X('count(Country):Q', title='Number of Disasters')
    ).transform_filter(
        brush
    ).add_selection(selector)

    hists = bars_climateChange2.mark_bar(opacity=0.5, thickness=100).encode(
        y=alt.Y('Adaptation action'),
        x=alt.X('Population'),
        tooltip='Population'
    ).transform_filter(
        selector
    )

    st.write((points_climateChange & bars_climateChange & hists).resolve_scale(color='independent'))

    st.markdown("""## Actions implemented by each country which led to a reduction in the CO2 levels""")
    country_list = list(data2['Country'].unique())
    input_dropdown = alt.binding_select(options=country_list, name='Country')
    selection = alt.selection_single(fields=['Country'], bind=input_dropdown, name='Country', init={'Country': "United States of America"})
    bars = alt.Chart(data2).mark_bar().encode(
        y='Country:N',
        color='Country:N',
        x='Population:Q'
    ).transform_filter(
        selection
    ).add_selection(selection)

    # Base chart for data tables
    ranked_text = alt.Chart(data2).mark_text().encode(
        y=alt.Y('row_number:O',axis=None)
    ).transform_window(
        row_number='row_number()'
    ).transform_filter(
        selection
    ).transform_window(
        rank='rank(row_number)'
    ).transform_filter(
        alt.datum.rank<20
    )

    # Data Tables
    carbon_level = ranked_text.encode(text='Estimated emissions reduction (metric tonnes CO2e):N').properties(title='Carbon level reduction in Metric Tonnes')
    implementation = ranked_text.encode(text ='Action Title:N').properties(title ='Action Title')

    text = alt.hconcat(implementation,carbon_level) # Combine data tables

    # Build chart
    st.write(alt.vconcat(
        text,
        bars
    ).resolve_legend(
        color="independent"
    ).configure_view(strokeWidth=0))

pages = ["Energy Consumption What If", "Energy Forecast", "Climate Change Impact"]

page = st.sidebar.selectbox(
        'Navigation',
        pages)
st.markdown("# Climate Change, Energy, and Global Responsibility")
# Create a multi-page app
# Source: https://towardsdatascience.com/creating-multipage-applications-using-streamlit-efficiently-b58a58134030
if page == pages[0]:
    per_capita_energy()
elif page == pages[1]:
    energy_forecast()
elif page == pages[2]:
    climate_change_impact()
