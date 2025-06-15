### Important Files
options_visual.py -> streamlit sricpt that visualizes all options for a specific day: ```streamlit run options_visual.py```
snapshot.py -> fits the functions for options at that moment
run.py -> tracks options over time and calculates a more stable function 

### File Overview
exchange.py -> Defines how broker interfaces must be implemented
deribit.py -> Implements the broker interface for the exchange Deribit
model.py -> function fitting
scale.py -> transforms the data in an range so that model.py methods work properly
options_downloader.py -> sricpt that downloads options for deribit every minute
