# gatling-scenario-graphs
A simple python script, which will consume the Gatling Logs to give a html page, which will have scenario based graphs.

## User manual for gatling-scenario-graphs v1.0

### Table of contents
- [Requirements](https://github.com/Navdit/gatling-scenario-graphs/blob/master/README.md#Requirements)
- [Setup from Scratch](https://github.com/Navdit/gatling-scenario-graphs#setup-from-scratch)
- [Quick Start](https://github.com/Navdit/gatling-scenario-graphs/blob/master/README.md#quick-start-example)
  - [Command to run script](https://github.com/Navdit/gatling-scenario-graphs#step-1-command-to-run-script)
  - [Checking out Graph](https://github.com/Navdit/gatling-scenario-graphs#step-2-checking-out-graph)
  - [Exploring Graph](https://github.com/Navdit/gatling-scenario-graphs#step-3-exploring-graph)
    

## Requirements
- Python 3 or up
- Pandas Library
- Bokeh Library

If you are newbie, then please refer to section - [Setup from Scratch](https://github.com/Navdit/gatling-scenario-graphs/blob/master/README.md#setup-from-scratch)

## Setup from Scratch

If you are running for the first time or have no clue how to setup, then follow these steps:

 - Setting up on Windows Machine:
    1. [Download latest release of Python.](https://www.python.org/downloads/windows/)
    2. [Install Pandas.](https://stackoverflow.com/questions/42907331/how-to-install-pandas-from-pip-on-windows-cmd)
    3. Install Bokeh:
    ```
        pip install bokeh
    ```

## Quick Start

#### Step 1: Command to run script

```
python create_gatling_scenario_graphs.py -i <location of Gatling Log Files separated by ,> -o <output location of the Graph HTML Page> -p <percentile>
```
Eg:
``` DOS 
python create_gatling_scenario_graphs.py -i C:\Logs\simulation_log1.log,C:\Logs\simulation_log2.log -o C:\Graphs\LoadTest_run1.html -p 99
```
**Arguments o and p are optional. Default value of:**
- **o is same folder as that of script.**
- **p is 95 percentile**

**Note: Log Files, should be given without any spaces**

If successful, you should see screen changes as follows:
![Run Screen](https://github.com/Navdit/gatling-scenario-graphs/blob/master/images/run_snapshot.PNG)

#### Step 2: Checking out Graph
A sample graphs looks like [this](https://github.com/Navdit/gatling-scenario-graphs/blob/master/graphs/GatlingScenarioGraphs.html). Please find below some sample screenshots.

**95th vs RPS (Requests Per Second)**
![95th vs RPS](https://github.com/Navdit/gatling-scenario-graphs/blob/master/images/rps_tab.PNG)

**95th vs Users**
![95th vs Users](https://github.com/Navdit/gatling-scenario-graphs/blob/master/images/users_tab.PNG)

**95th vs Errors**
![95th vs Users](https://github.com/Navdit/gatling-scenario-graphs/blob/master/images/errors_tab.PNG)

#### Step 3: Exploring Graph

Graph can be explored by using following tools:
- Zoom in ![zoom](https://github.com/Navdit/gatling-scenario-graphs/blob/master/images/zoom.PNG)
- Reset Graph ![reset](https://github.com/Navdit/gatling-scenario-graphs/blob/master/images/reset.PNG)
- Save Graph as PNG ![save](https://github.com/Navdit/gatling-scenario-graphs/blob/master/images/save.PNG) 
- Hover ![hover](https://github.com/Navdit/gatling-scenario-graphs/blob/master/images/hover.PNG)

These tools can be found in the toolbar present under every plot. Toolbar looks like:
![select_deselect](https://github.com/Navdit/gatling-scenario-graphs/blob/master/images/select_deselect.PNG)

- Select/Deselect Transactions from Legend, as shown below:
![toolbar](https://github.com/Navdit/gatling-scenario-graphs/blob/master/images/toolbar.PNG)

- When Hover and Zoom are selected, a Graph would like as below:
![hover_zoom_selected](https://github.com/Navdit/gatling-scenario-graphs/blob/master/images/hover_zoom_selected.PNG)

