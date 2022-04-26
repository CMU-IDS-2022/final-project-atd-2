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

# @st.cache
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
    if with_coords == False:
        return energy_sources
    lats = pd.read_csv('./data/average-latitude-longitude-countries.csv')

    energy_sources = energy_sources[energy_sources.Entity != 'Europe']
    country_lat = energy_sources.merge(lats, left_on='Entity', right_on='Country')
    return country_lat

# @st.cache
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

    df = get_energy(with_coords)
    df['Entity'] = df.Entity.astype('str')
    joined = population.merge(df, on='Entity')
    joined['EnergyPerCapita'] = joined['TotalEnergy']/joined['Population (historical estimates and future projections)']
    if with_coords:
        joined['Latitude_x'] = joined['Latitude']
        joined['Longitude_x'] = joined['Longitude']
    return joined

# @st.cache
def get_fuelco2():
    fuel_co2 = pd.read_csv('./data/co2-emissions-by-fuel-line.csv')
    fuel_co2 = fuel_co2[(fuel_co2.Year == 2019)]
    co2_cols = ['Annual CO2 emissions from oil', 'Annual CO2 emissions from flaring', 'Annual CO2 emissions from cement', 'Annual CO2 emissions from coal', 'Annual CO2 emissions from gas', 'Annual CO2 emissions from other industry']
    co2_rename = ['Oil', 'Flaring', 'Cement', 'Coal', 'Gas', 'Other Industries']
    fuel_co2 = fuel_co2.rename(index=str, columns=dict(zip(co2_cols, co2_rename)))
    fuel_co2['NetCO2'] = 0
    for col in co2_rename:
        fuel_co2[col] = fuel_co2[col].fillna(0)
        fuel_co2['NetCO2'] += fuel_co2[col]
    
    co2_cols = co2_rename
    population = pd.read_csv('./data/population-past-future.csv')
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
        co2_pc[col + '_WORLD'] = co2_pc[col+'_PC']*world_population
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
    energy_sources.loc[(energy_sources.Entity == 'United States'), ['Entity']] = 'United States of America'
    color_range = alt.Color('TotalEnergy:Q', 
                       scale=alt.Scale(
                        type='pow', exponent=0.6, 
                        range=['yellow', 'orange', 'red']
                    ))
    base_chart = alt.Chart(countries,
        title='Net Energy Consumption by Country'
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
    energy_pc.loc[(energy_pc.Entity == 'United States'), ['Entity']] = 'United States of America'
    pc_chart = alt.Chart(countries,
        title='Per Capita Energy Consumption by Country'
    ).mark_geoshape(stroke='white').encode(
        color=alt.condition(selector, alt.Color('EnergyPerCapita:Q', 
                       scale=alt.Scale(
                        type='pow', exponent=0.6, 
                        range=['yellow', 'orange', 'red']
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

"""

## Energy Consumption and CO2 Emissions

"""


"""
Energy production is the major driving force behind climate change. Energy production is driven by energy needs which can vary by country.
"""
geo_map1, geo_map2, selector = get_energypc_chart_heatmap()

per_capita = st.checkbox("Show Per Capita Energy")


co2_pc, co2_cols = get_fuelco2()
co2_pc.loc[(co2_pc.Entity == 'United States'), ['Entity']] = 'United States of America'
# co2_pc_world = co2_pc[co2_pc.Entity == 'World']
# net_world_co2 = co2_pc[co2_pc.Entity == 'World'].NetCO2_WORLD.max()
co2_pc = co2_pc[co2_pc.Entity != 'World']
net_world_co2 = co2_pc['NetCO2_WORLD'].mean()
fuel_co2_long_2 = co2_pc.melt(id_vars='Entity', value_vars=list(map(lambda x: x + "_WORLD", co2_cols)))

co2_chart = alt.Chart(
    fuel_co2_long_2,
    title='CO2 Emissions by Fuel Type Based on Selected Country\'s Rate'
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
        'Red mark': "Original Net CO2 Emissions"
    })
netCO2_rule_chart = alt.Chart(netCO2_Line).mark_rule().encode(
    y=alt.Y('CO2 emissions(T):Q', title='CO2 emissions(T)'),
    color = alt.Color('Red mark', scale = alt.Scale(range=['red']))
).properties(
    width=200,
    height=200
)

fuel_co2_long_full = co2_pc.melt(id_vars='Entity', value_vars=['NetCO2_WORLD'])
co2_chart_full = alt.Chart(
    fuel_co2_long_full,
    title='Net Global CO2 Emissions Based on Selected Country\'s Rate'
).mark_bar().encode(
    x=alt.X('variable', title='World'), 
    y=alt.Y('mean(value):Q', title='CO2 emissions(T)'),
    tooltip = [alt.Tooltip('mean(value):Q', title='CO2 emissions (T)')]
).properties(
        width=200,
        height=200
).transform_filter(
            selector
).add_selection(selector) + netCO2_rule_chart


if per_capita:
    st.write(((geo_map1 | geo_map2).resolve_scale(color='independent') & (co2_chart | co2_chart_full)).resolve_scale(color='independent'))
else:
    st.write(geo_map1)




"""

### Predicting energy production and demand based on current growth rate

"""



def load_data():
    energy_data = pd.read_csv("./data/owid-energy-data.csv")
    return energy_data.sort_index()

energy_data = load_data()
all_countries = list(set(energy_data["country"]))

all_countries.sort()
option = st.selectbox(
     'Select a Country:',
     all_countries)

energy_ukr = energy_data[energy_data['country']==option]

energy_ukr = energy_ukr.dropna(subset = ['electricity_demand'])

try:

  x_years = list(energy_ukr['year']) + list(range(2023,2030))



  # st.write("Electricity Demand Historic Data and Prediction")
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

  st.write("Electricity Demand and Generation Historic Data and Prediction")
  st.write("In the plot below, the points marked upto 2022 are actual historical values and the lines are the predictions for electricity demand and generation.")

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

except Exception as e:
  print(e)
  st.write("Not enough data for this country!")






data = pd.read_csv("./data/Dataset1.csv")


data2 = pd.read_csv("./data/emmission.csv")



data2 = data2.dropna()



data = data.dropna()



"""# Climate Hazards of Each country and the Adaption Action"""
brush = alt.selection(type='interval')
selector = alt.selection_single(empty='all', fields=['Country'])

"""Select plots on the graph to see the climate hazards occuring in the following countries"""


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

"""Select the Country to view the adaption action implemented"""

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
    x=alt.X('Adaptation action'),
    y=alt.Y('Population'),
    tooltip='Population'
).transform_filter(
    selector
)

points_climateChange & bars_climateChange & hists