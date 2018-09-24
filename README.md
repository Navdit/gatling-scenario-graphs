# gatling-scenario-graphs
A simple python script, which will consume the Gatling Logs to give a html page, which will have scenario based graphs.

## User manual for gatling-scenario-graphs v1.0

### Table of contents
- [Requirements](https://github.com/Navdit/gatling-scenario-graphs/blob/master/README.md#Requirements)
[Quick Start Example](https://github.com/Navdit/gatling-scenario-graphs/blob/master/README.md#quick-start-example)
    

## Requirements
- Python 3 or up
- Pandas Library
- Bokeh Library

If you are newbie, then please refer to section - [Setup from Scratch](https://github.com/Navdit/gatling-scenario-graphs/blob/master/README.md#setup-from-scratch)

## Setup from Scratch

If you are running for the first time or have no clue how to setup, then follow these steps:

 - Setting up on Windows Machine:
    1. [Download latest release of Python.](https://www.python.org/downloads/windows/)
    2. [Pip install Pandas.](https://stackoverflow.com/questions/42907331/how-to-install-pandas-from-pip-on-windows-cmd)
    3. Pip install Bokeh using command:
    ```
        pip install bokeh
    ```

## Quick Start Example

#### Step 1: In command prompt 

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
A sample graphs looks like [this](https://github.com/Navdit/gatling-scenario-graphs/blob/master/graphs/GatlingScenarioGraphs.html).

Please find below the sample screenshots.
