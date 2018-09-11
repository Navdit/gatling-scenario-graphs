# ============================================================================================================
# Purpose:           Generates the Scenario Based Graphs using Gatling Simulation.
# Author:            Navdit Sharma (Nav)
# Notes:             Script reads its inputs from the given config File.
#                    Parameters read from config file are:
#                    1. Simulation Logs
# Revision:          Last change: 05/09/18 by Nav :: Created and tested the script
# ==============================================================================================================

import pandas as pd
from pathlib import Path
import time
import getopt
import sys
import logging

from bokeh.layouts import Column
from bokeh.models import (HoverTool, Legend, LinearAxis, Range1d, ColumnDataSource)
from bokeh.models.formatters import DatetimeTickFormatter
from bokeh.palettes import d3
from bokeh.plotting import figure, output_file, show


##################################################################################################################
# Function Name: Generate_Gatling_Log_Df
# Description  : Consumes the Gatling Logs and Return a clean Dataframe which can be used by other functions
# @param       : List of Simulation Logs 
# @return      : Dataframe gat_log_graph_df with columns: [Owner,Scenario,Transaction_Name,Status,ResponseTime,
#                LocalTime]
# Author       : Navdit Sharma
# Comments     : Created on 05/09/2018 
##################################################################################################################
def generate_gatling_log_df(simulation_logs_list):
    # Column Names
    gat_log_col_names = ["Owner", "Scenario", "ThreadId", "JunkCol1",
                         "Transaction_Name", "StartTime", "EndTime", "Status"]

    # Reading into Dataframe
    gat_log_df = pd.read_csv(simulation_logs_list[0], sep='\t', header=None, names=gat_log_col_names, dtype=str)
    for index in range(len(simulation_logs_list)-1):
        gat_log_df_1 = pd.read_csv(simulation_logs_list[index+1], sep='\t', header=None, names=gat_log_col_names, dtype=str)
        gat_log_df = gat_log_df.append(gat_log_df_1)

    gat_log_df = gat_log_df.reset_index(drop=True)
    gat_log_df.to_csv("temp.csv")

    # Fill NaN values with default value
    gat_log_df = gat_log_df.fillna("0")

    # Get Dataframe for Graphs
    gat_log_graph_df = gat_log_df.loc[gat_log_df["Status"] != "KO"]
    gat_log_graph_df = gat_log_graph_df[gat_log_graph_df["Owner"] != "GROUP"]
    gat_log_graph_df = gat_log_graph_df[gat_log_graph_df["Owner"] != "RUN"]

    # Set correct dtypes
    gat_log_graph_df[['StartTime', 'EndTime']] = gat_log_graph_df[['StartTime', 'EndTime']].apply(pd.to_numeric)

    # Calculate Response Time
    gat_log_graph_df["ResponseTime"] = gat_log_graph_df.EndTime - gat_log_graph_df.StartTime
    gat_log_graph_df[['StartTime', 'EndTime']] = gat_log_graph_df[['StartTime', 'EndTime']].apply(pd.to_numeric)
    gat_log_graph_df['LocalTime'] = gat_log_graph_df['StartTime'] + (10 * 60 * 60 * 1000)

    # Drop Unnecessary Columns
    gat_log_graph_df = gat_log_graph_df.drop(["JunkCol1"], axis=1)
    gat_log_graph_df = gat_log_graph_df.drop(["ThreadId"], axis=1)
    gat_log_graph_df = gat_log_graph_df.drop(["StartTime"], axis=1)
    gat_log_graph_df = gat_log_graph_df.drop(["EndTime"], axis=1)

    return gat_log_graph_df

########################################################################################################################


##################################################################################################################
# Function Name: Get_Scenario_Metrics
# Description  : Calculates the RPS, NinetyFifth of the given scenario
# @param       : Scenario Name
# @param       : Gatling Log Dataframe
# @return      : Dataframe scenario_metrics_df with columns: [LocalTime, RPS, ${TransactionNames}]
# @return      : Dataframe overall_transaction_ninety_fifth_df with columns: [Transaction, NinetyFifth]
# Author       : Navdit Sharma
# Comments     : Created on 05/09/2018 
##################################################################################################################
def get_scenario_metrics(scenario_name, gatling_log_df):
    # Set the index
    row_count = len(gatling_log_df.index)
    
    # Create new Scenario Dataframe
    cond_col = gatling_log_df['Scenario'] == scenario_name
    scenario_temp_df = gatling_log_df[cond_col]

    # Transactions OK DF
    scenario_ok_df = scenario_temp_df.loc[scenario_temp_df["Status"] == "OK"]

    # Active Threads DF
    scenario_rps_df = scenario_temp_df.loc[scenario_temp_df["Owner"] == "REQUEST"]

    # New Dataframe
    scenario_metrics_df = pd.DataFrame(columns=["LocalTime"])

    # Create temp DF for RPS
    scenario_rps_temp_df = pd.DataFrame(columns=["LocalTime", "RPS"])
    
    # Start Begin and End Time
    begin_time = scenario_rps_df["LocalTime"][scenario_rps_df.index[0]]
    end_time = scenario_rps_df["LocalTime"][scenario_rps_df.index[-1]]

    # Entry when rps would have been zero 1 sec prior to test
    scenario_rps_temp_df.loc[0] = (begin_time - 1000, 0)

    # Just get Divisor to know how many loops to go through
    loop_count = (end_time - begin_time) // 1000

    for i in range(loop_count):
        end_time = begin_time + 1000
        tmp_df = scenario_rps_df[
            (scenario_rps_df["LocalTime"] >= begin_time) & (scenario_rps_df["LocalTime"] <= end_time)]
        # rps = rps + tmp_df["Scenario"].count()
        rps = tmp_df["Scenario"].count()
        scenario_rps_temp_df.loc[i + row_count] = [begin_time, rps]
        begin_time = end_time

    # To calculate for the last TimeInterval
    end_time = scenario_rps_df["LocalTime"][scenario_rps_df.index[-1]]
    tmp_df = scenario_rps_df[(scenario_rps_df["LocalTime"] >= begin_time) &
                               (scenario_rps_df["LocalTime"] <= end_time)]
    rps = tmp_df["Scenario"].count()
    scenario_rps_temp_df.loc[-1] = [begin_time, rps]

    # Refresh the index
    scenario_rps_temp_df = scenario_rps_temp_df.reset_index(drop=True)
    scenario_rps_temp_df = scenario_rps_temp_df.applymap(str)

    # Merge the dataframe of RPS
    scenario_metrics_df = scenario_metrics_df.merge(scenario_rps_temp_df, on='LocalTime', how='outer')

    # Overall NinetyFifth
    overall_transaction_ninety_fifth_df = pd.DataFrame(columns=["Transaction", "NinetyFifth"])

    # Get the transaction list in the scenario
    transactions_list = scenario_ok_df.Transaction_Name.unique().tolist()

    # for i in range(len(scenario_list)):
    for transaction_index in range(len(transactions_list)):
        transaction_name = transactions_list[transaction_index]

        # Make DF for transaction
        temp_df = pd.DataFrame(columns=["LocalTime", "TransactionName"])

        # Create new Transaction Dataframe
        transaction_df = scenario_ok_df[scenario_ok_df['Transaction_Name'] == transaction_name]

        # Calculate the overall 95th of the Transaction
        overall_transaction_ninety_fifth_df.loc[transaction_index] = \
            [transaction_name, transaction_df.ResponseTime.quantile(0.95)]

        # Start Begin and End Time
        begin_time = transaction_df["LocalTime"][transaction_df.index[0]]
        end_time = transaction_df["LocalTime"][transaction_df.index[-1]]

        # Just get Divisor
        loop_count = (end_time - begin_time) // 1000

        for i in range(loop_count):
            end_time = begin_time + 1000
            tmp_df = transaction_df[
                (transaction_df["LocalTime"] >= begin_time) & (transaction_df["LocalTime"] <= end_time)]
            temp_df.loc[i + row_count] = [begin_time, tmp_df.ResponseTime.quantile(0.95)]
            begin_time = end_time

        # To calculate for the last TimeInterval
        end_time = transaction_df["LocalTime"][transaction_df.index[-1]]
        tmp_df = transaction_df[(transaction_df["LocalTime"] >= begin_time) & (transaction_df["LocalTime"] <= end_time)]
        temp_df.loc[-1] = [begin_time, tmp_df.ResponseTime.quantile(0.95)]

        # Clean the Dataframe from NaN values
        temp_df = temp_df.dropna(how='any')

        # Refresh the index
        temp_df = temp_df.reset_index(drop=True)

        # Rename the columns and set datatype to str of all values
        temp_df.rename(columns={'TransactionName': transaction_name}, inplace=True)
        temp_df = temp_df.applymap(str)

        # Join two Dataframes
        scenario_metrics_df = scenario_metrics_df.merge(temp_df, on='LocalTime', how='outer')

    # Changing LocalTime to DateTime and sort the Time in Ascending order
    scenario_metrics_df['LocalTime'] = pd.to_datetime(scenario_metrics_df['LocalTime'], unit='ms')
    scenario_metrics_df = scenario_metrics_df.sort_values("LocalTime", ascending=True)

    # Add the Steady State Users which are not filled
    scenario_metrics_df["RPS"] = scenario_metrics_df["RPS"].ffill()

    # Fill NaN values with zero
    scenario_metrics_df = scenario_metrics_df.fillna(0)

    # Return Two Dataframes
    return scenario_metrics_df, overall_transaction_ninety_fifth_df

########################################################################################################################


########################################################################################################################
# Function Name: check_path
# Description  : Take the location of file/directory and check if it exists. Else throw the exception.
# @param       : Path to be checked
########################################################################################################################
def check_path(input_path):
    if not input_path.exists():
        raise Exception("File don't exist. Please check path {}".format(input_path))

########################################################################################################################


########################################################################################################################
# Function Name: check_logs_path
# Description  : Checks the path of the log files.
# @param       : List of Log Paths
########################################################################################################################
def check_logs_path(input_logs_list):
    simulation_logs_list = strip_list(input_logs_list.split(','))
    for logs in simulation_logs_list:
        file_loc = Path(logs)
        check_path(file_loc)

    return simulation_logs_list

########################################################################################################################


########################################################################################################################
# Function Name: strip_list
# Description  : Take a list of string objects and return the same list stripped of extra whitespace.
# @param       : List which needs to be stripped of the extra white spaces
# @return      : The same list, which was given as input but stripped of whitespaces
########################################################################################################################
def strip_list(list_input):
    return [x.strip() for x in list_input]

########################################################################################################################


########################################################################################################################
# Function Name: validate_user_given_arguments
# Description  : Validates the input given by the user to the python script
# @param       : Arguments given by user
# @return      : List of the Simulation Log Files
# @return      : If given, path of the Graph, where the user wants to get generated
########################################################################################################################
def validate_user_given_arguments(argv):
    # Arguments
    version = '1.0'
    verbose = False
    output_graph_path = 'GatlingScenarioGraphs_RPS.html'
    input_log = ""

    # print('ARGV      : {}'.format(sys.argv[1:]))

    options, remainder = getopt.getopt(sys.argv[1:], 'i:o:v', ['input=',
                                                               'output=',
                                                               'verbose',
                                                               'version=',
                                                               ])
    # print('OPTIONS   : {}'.format(options))

    for opt, arg in options:
        if opt in ('-o', '--output_graph'):
            output_graph_path = arg
        elif opt in ('-i', '--simulation_log'):
            input_log = arg
        elif opt in ('-v', '--verbose'):
            verbose = True
        elif opt == '--version':
            version = arg

    # print('VERSION   : {}'.format(version))
    # print('VERBOSE   : {}'.format(verbose))
    # print('OUTPUT    : {}'.format(output_graph_path))
    # print('LOG FILES : {}'.format(input_log))
    # print('REMAINING : {}'.format(remainder))

    return input_log, output_graph_path

########################################################################################################################


########################################################################################################################
# Function Name: get_list_of_scenarios
# Description  : Gives the sorted list of the scenarios, which were run in the Gatling Test
# @param       : Gatling Log Dataframe
# @return      : Sorted List of Scenarios
########################################################################################################################
def get_list_of_scenarios(gatling_log_df):
    sorted_scenario_list = gatling_log_df.Scenario.unique().tolist()
    sorted_scenario_list.sort()
    return sorted_scenario_list

########################################################################################################################


########################################################################################################################
# Function Name: remove_dollar_sign_and_get_column_names_dict
# Description  : It removes the dollar sign from the column name and transaction names of df and returns the dictionary
#                of the old and new column names. Reason - Having "$" in the name of the column screws the Hover
#                Tool of Bokeh. Having dictionary will help to keep the legend names same as the ones found in Gatling
#                Report, but Hover tool
#                will show the name without "$" sign.
# @param       : Scenario Metrics Dataframe and Overall Ninety Fifth Dataframe.
# @return      : Dictionary of Column Names
########################################################################################################################
def remove_dollar_sign_and_get_column_names_dict(scenario_metrics_df, overall_ninety_fifth_df):
    col_name_dict = {}
    for column in scenario_metrics_df:
        new_col_name = column.replace("$", "")
        scenario_metrics_df.rename(columns={column: new_col_name}, inplace=True)
        overall_ninety_fifth_df['Transaction'] = \
            overall_ninety_fifth_df['Transaction'].replace(column, new_col_name)
        col_name_dict[new_col_name] = column
    
    return col_name_dict

########################################################################################################################


########################################################################################################################
# Function Name: get_y_range_of_graph
# Description  : Gives the Right and Left Y-axis range of the graph based on the max value in dataframe
# @param       : Scenario Metrics Dataframe
# @return      : Left and Right Y-Axis Range of Bokeh Graph
########################################################################################################################
def get_y_range_of_graph(scenario_metrics_df):
    tmp_max_val_df = scenario_metrics_df
    tmp_max_val_df = tmp_max_val_df.apply(pd.to_numeric)

    # Right y-Axis Range
    right_y_axis_range = tmp_max_val_df['RPS'].max() + 1

    # Left y-axis Range
    tmp_max_val_df = tmp_max_val_df.drop(["LocalTime"], axis=1)
    tmp_max_val_df = tmp_max_val_df.drop(["RPS"], axis=1)
    left_y_axis_range = (0, tmp_max_val_df.values.max() + 50)

    return left_y_axis_range, right_y_axis_range

########################################################################################################################


########################################################################################################################
# Function Name: get_color_palette
# Description  : To set the color palette, which will be used in plotting Bokeh Graph
# @param       : Scenario Metrics Dataframe
# @param       : Scenario Name, for which the Color Palette has to be set
# @return      : Color Palette
########################################################################################################################
def get_color_palette(scenario_metrics_df, scenario):
    # Number of Lines to plot
    num_lines = len(scenario_metrics_df.columns)

    # Get the colors
    if num_lines > 20:
        raise Exception("At present maximum of 19 transactions/scenario is permissible. "
                        "Please check Scenario {}, which has {} transactions".format(scenario, num_lines))
    elif num_lines < 3:
        color_palette = ['#1f77b4', '#2ca02c']
    else:
        color_palette = d3['Category20'][num_lines]

        # Removing Red Color which is on index 5
        if "#d62728" in color_palette:
            color_palette.remove("#d62728")

    return color_palette

########################################################################################################################


########################################################################################################################
# Function Name: set_hover_tool_tips
# Description  : Set the properties of the hover tool tips.
# @return      : hover_tool_tips
########################################################################################################################
def set_hover_tool_tips():
    hover_tool_tips = HoverTool(
        tooltips=[
            ('Time', '$x{%F %T}'),
            ("Metric", "$name"),
            ("Value", "@$name")
        ],
        formatters={'$x': 'datetime', '@$name': 'printf'},
        mode='mouse'  # display a tooltip whenever the cursor is vertically in line with a glyph
    )

    return hover_tool_tips

########################################################################################################################


########################################################################################################################
# Function Name: plot_new_graph
# Description  : Set the properties of the hover tool tips.
# @return      : hover_tool_tips
########################################################################################################################
def plot_new_graph(x_axis_label, x_axis_type, y_axis_label, plot_width, plot_height,
                   left_y_range, toolbar_location, tools_to_show):
    plot = figure(x_axis_label=x_axis_label,
                  x_axis_type=x_axis_type,
                  y_axis_label=y_axis_label,
                  plot_width=plot_width,
                  plot_height=plot_height,
                  y_range=left_y_range,
                  toolbar_location=toolbar_location,
                  tools=tools_to_show)

    return plot

########################################################################################################################


########################################################################################################################
# Function Name: set_graph_and_legend_properties
# Description  : Sets the Properties of the graph and the legend of the graph
# @param       : Graph and the legend it will be using, Scenario Name
# @return      : Returns the plotted graph with the properties
########################################################################################################################
def set_graph_and_legend_properties(plot_graph, legends, scenario):
    # Add Tool - Hovertool
    # Hover Tool Properties
    hover_tool_tips = set_hover_tool_tips()
    plot_graph.add_tools(hover_tool_tips)

    # Legend related formatting
    legend = Legend(items=legends, location=(0, 0))
    legend.click_policy = "hide"
    legend.background_fill_color = "#2F2F2F"
    legend.label_text_color = "white"
    legend.border_line_color = "#2F2F2F"
    legend.inactive_fill_color = "#2F2F2F"
    plot_graph.add_layout(legend, 'right')

    # X-Axis related formatting
    plot_graph.xgrid.grid_line_color = "white"
    plot_graph.xgrid.grid_line_dash = [6, 4]
    plot_graph.xgrid.grid_line_alpha = .3
    plot_graph.xaxis.axis_line_color = "white"
    plot_graph.xaxis.axis_label_text_color = "white"
    plot_graph.xaxis.major_label_text_color = "white"
    plot_graph.xaxis.major_tick_line_color = "white"
    plot_graph.xaxis.minor_tick_line_color = "white"
    plot_graph.xaxis.formatter = DatetimeTickFormatter(
        microseconds=["%H:%M:%S"],
        milliseconds=["%H:%M:%S"],
        seconds=["%H:%M:%S"],
        minsec=["%H:%M:%S"],
        minutes=["%H:%M"],
        hourmin=["%H:%M"],
        hours=["%H:%M"],
        days=["%H:%M"],
        months=["%H:%M"],
        years=["%H:%M"], )

    # Y-axis related formatting
    plot_graph.ygrid.grid_line_color = "white"
    plot_graph.ygrid.grid_line_dash = [6, 4]
    plot_graph.ygrid.grid_line_alpha = .3
    plot_graph.yaxis.axis_line_color = "white"
    plot_graph.yaxis.axis_label_text_color = "white"
    plot_graph.yaxis.major_label_text_color = "white"
    plot_graph.yaxis.major_tick_line_color = "white"
    plot_graph.yaxis.minor_tick_line_color = "white"

    # Graph related Formatting
    plot_graph.min_border_left = 80
    plot_graph.title.text = scenario
    plot_graph.title.text_color = "white"
    plot_graph.title.text_font = "times"
    plot_graph.title.text_font_style = "normal"
    plot_graph.title.text_font_size = "14pt"
    plot_graph.title.align = "center"
    plot_graph.background_fill_color = '#2F2F2F'
    plot_graph.border_fill_color = '#2F2F2F'
    plot_graph.outline_line_color = '#444444'

    return plot_graph

########################################################################################################################


########################################################################################################################
# Function Name: plot_graph_by_transaction
# Description  : Plots the graph of all the transactions in a given scenario
# @param       : Given Scenario - scenario_metrics_df
# @param       : overall_ninety_fifth_df
# @param       : Scenario Name
# @return      : List of Plotted graphs along with Legends in Legend List
# @return      : Figure of the graph
########################################################################################################################
def plot_graph_by_transaction(scenario_metrics_df, overall_ninety_fifth_df, scenario):
    # Remove $ from the names of column names of scenario_metrics_df and
    # Rename the Transactions of overall_ninety_fifth_df
    col_name_dict = remove_dollar_sign_and_get_column_names_dict(scenario_metrics_df, overall_ninety_fifth_df)

    # Define Y-Axis Range of the Graph
    (left_y_range, right_y_range) = get_y_range_of_graph(scenario_metrics_df)

    # Get the colors for the Lines of the Graph
    color_palette = get_color_palette(scenario_metrics_df, scenario)

    # Tools to be available in graph
    tools_to_show = 'box_zoom,reset,save'

    # create a new plot with a title and axis labels
    scenario_graph = plot_new_graph('Time', 'datetime', 'Response Time (ms)', 1900, 400, left_y_range, 'below', tools_to_show)

    # Disabling Hover Tool
    scenario_graph.toolbar.active_inspect = None

    # Index to go through Color Palette
    color_index = 0

    # get all the legends in one list
    legend_list = []

    # Source of Graphs
    source = ColumnDataSource(scenario_metrics_df)

    # Plot graph transaction-wise
    for col_name in scenario_metrics_df.columns:
        # Ignore Column LocalTime
        if col_name not in "LocalTime":
            if col_name in "RPS":
                # Get the legend name
                legend_name = "Throughput (RPS)"

                # Setting the second y axis range name and range
                scenario_graph.extra_y_ranges = {"RPS": Range1d(0, right_y_range)}

                # Adding the second axis to the plot.
                scenario_graph.add_layout(LinearAxis(y_range_name="RPS", axis_label="Throughput (RPS)"), 'right')

                # PlotGraph
                plot_graph = scenario_graph.line('LocalTime',
                                                 col_name,
                                                 source=source,
                                                 line_width=2,
                                                 color="orange",
                                                 y_range_name="RPS",
                                                 name=col_name)

            else:
                # Transaction 95th
                col_ninety_fifth = int(overall_ninety_fifth_df.loc
                                       [overall_ninety_fifth_df['Transaction'] == col_name, 'NinetyFifth'].item())

                # Get the legend name along with Transaction's 95th
                legend_name = col_name_dict[col_name] + " (95th: {} ms)".format(col_ninety_fifth)

                # PlotGraph
                plot_graph = scenario_graph.line('LocalTime',
                                                 col_name,
                                                 source=source,
                                                 line_width=2,
                                                 color=color_palette[color_index],
                                                 name=col_name)

            # increment through color palette
            color_index = color_index + 1

            # Append the legend
            legend_list.append((legend_name, [plot_graph]))

    # Append the graph in list which will be passed to "Column"
    scenario_graph_final = set_graph_and_legend_properties(scenario_graph, legend_list, scenario)

    return scenario_graph_final

########################################################################################################################


########################################################################################################################
# Function Name: generate_graph
# Description  : It generates the graph based on the Dataframe made on the Simulation Log
# @param       : Dataframe of the Gatling Logs
# @param       : Path where the Graph needs to generated
# @param       : Check, whether to show or not once the graph is generated
# @return      : Null
########################################################################################################################
def generate_graph(gat_log_df, graph_output_path, show_graph=False):
    # Get the List of Scenarios in Test Run
    scenario_list = get_list_of_scenarios(gat_log_df)

    # Set Graph Output File
    output_file(graph_output_path)

    # Empty List to contain individual scenario graphs
    scenario_plots = []

    # Looping over Scenarios in Test
    for scnIndex in range(len(scenario_list)):
        # Get the scenario Name
        scenario_name = scenario_list[scnIndex]

        # Get scenario_metrics_df and overall_ninety_fifth_df
        (scenario_metrics_df, overall_ninety_fifth_df) = get_scenario_metrics(scenario_name, gat_log_df)

        # Plot Graphs of the Transactions in Scenario
        complete_scenario_graph = plot_graph_by_transaction(scenario_metrics_df, overall_ninety_fifth_df, scenario_name)

        # Add the Scenario Graphs to the Final Combined Graph
        scenario_plots.append(complete_scenario_graph)

        print("{} Completed.".format(scenario_name))
        logger.info("{} Completed.".format(scenario_name))

    # put all the plots in a Column
    layout = Column(children=scenario_plots, sizing_mode='stretch_both')

    # Display Graph once done
    if show_graph:
        show(layout)

########################################################################################################################


########################################################################################################################
# Function Name: main
# Description  : Calls the functions to consume Excel given by the user and update the scenarios
# @param       : Null
# @return      : Null
########################################################################################################################
def main(argv):

    # Get the Log Files Location and Output Graph Location
    simulation_logs, output_graph = validate_user_given_arguments(argv)

    # Check if Log Files Exist
    simulation_logs_list = check_logs_path(simulation_logs)

    # Generate Combined Gatling Log Dataframe
    gat_log_graph_df = generate_gatling_log_df(simulation_logs_list)

    # Generate Graph
    generate_graph(gat_log_graph_df, output_graph, True)

##################################################################################################################


##################################################################################################################
# Function Name: __main__
# Description  : Entry Point of the script
# @param       : Null
# @return      : Null
##################################################################################################################
if __name__ == "__main__":
    print("Script Started")
    # Start Time of Code
    start_time = time.time()

    # Setting Logger
    logsLocation = "GatlingScenarioGraphs.log"

    logger = logging.getLogger("Gatling_Scenario_Graphs")
    logger.setLevel(logging.INFO)

    # create a file handler
    handler = logging.FileHandler(logsLocation)
    handler.setLevel(logging.INFO)

    # create a logging format
    formatter = logging.Formatter('%(asctime)s %(message)s', datefmt='%m/%d/%Y %I:%M:%S %p')
    handler.setFormatter(formatter)

    # add the handlers to the logger
    logger.addHandler(handler)

    logger.info("Script Started")

    # Call the main function
    main(sys.argv[1:])

    # Print Time taken to execute script
    logger.info("CUSTOM INFO : --- Script Execution Time: %s seconds ---" % (time.time() - start_time))
    print("CUSTOM INFO : --- Script Execution Time: %s seconds ---" % (time.time() - start_time))

##################################################################################################################
