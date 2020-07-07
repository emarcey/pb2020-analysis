# pb2020-analysis

Analysis tools based on work from the [r2020PoliceBrutality project](https://github.com/2020PB/police-brutality)

### Analysis Performed

1. Fetch data from the [data build of 2020PB/police-brutality](https://github.com/2020PB/police-brutality/blob/data_build/all-locations-v2.json)
2. Aggregate incidents by city
3. Get city populations
4. Filter on min_incidents and min_population
5. Output results with incidents per 100k residents.


#### Args

```
--min_incidents: minimum number of incidents for a city to be included (Default is 10)
--min_population: minimum population of city proper (not metro) for a city to be included (Default is 100,000)
```
