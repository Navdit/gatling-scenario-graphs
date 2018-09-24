# ============================================================================================================
# Purpose:           Generates the Scenario Based Graphs using Gatling Simulation Log.
# Author:            Navdit Sharma (Nav)
# Notes:             Run the script from command prompt.
# Revision:          Last change: 05/09/18 by Nav :: Created and tested the script
# ==============================================================================================================

import getopt
import logging
import sys
import time
from pathlib import Path

import pandas as pd
from bokeh.layouts import Column
from bokeh.models import (ColumnDataSource, HoverTool, Legend, LinearAxis,
                          Range1d)
from bokeh.models.formatters import DatetimeTickFormatter
from bokeh.models.widgets import Panel, Tabs
from bokeh.palettes import d3
from bokeh.plotting import figure, output_file, save


##################################################################################################################
# Function Name: Generate_Gatling_Log_Df
# Description  : Consumes the Gatling Logs and Return a clean Dataframe which can be used by other functions
# @param       : List of Simulation Logs 
# @return      : Dataframe gat_log_graph_df with columns: [Owner,Scenario,Transaction_Name,Status,ResponseTime,
#                LocalTime]
# Author       : Navdit Sharma
# Comments     : Created on 05/09/2018 
##################################################################################################################
def generate_gatling_log_df(simulation_logs_list: list) -> pd.DataFrame:
    # Column Names
    gat_log_col_names = ["Owner", "Scenario", "ThreadId", "JunkCol1",
                         "Transaction_Name", "StartTime", "EndTime", "Status"]

    # Reading into Dataframe
    gat_log_df = pd.read_csv(simulation_logs_list[0], sep='\t', header=None, names=gat_log_col_names, dtype=str)
    for index in range(len(simulation_logs_list) - 1):
        gat_log_df_1 = pd.read_csv(simulation_logs_list[index + 1], sep='\t', header=None,
                                   names=gat_log_col_names, dtype=str)
        gat_log_df = gat_log_df.append(gat_log_df_1)

    # Reset the index of the dataframe
    gat_log_df = gat_log_df.reset_index(drop=True)

    # Get Dataframe for Graphs
    gat_log_graph_df = gat_log_df[gat_log_df["Owner"] != "GROUP"]
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


########################################################################################################################
# Function Name: merge_right_y_axis_values_with_scenario_df
# Description  : Computes the  values of right y-axis in the given scenario df based on given right_y_axis_filter
# @param       : Dataframe - which has values for that filter. Columns are:
#                [Owner,Scenario, Transaction_Name, Status, ResponseTime, LocalTime]
# @param       : right-y-axis filter which can be: Users, Errors, RPS and RPM
# @param       : granularity at which the values have to be calculated.
# @return      : Dataframe scenario_metrics_df with columns: [LocalTime, ${filter}]
# Author       : Navdit Sharma
# Comments     : Created on 05/09/2018
########################################################################################################################
def compute_right_y_axis(scenario_right_y_axis_df: pd.DataFrame, right_y_axis_filter: str, granularity: int) \
        -> pd.DataFrame:
    # Initialise Users
    if right_y_axis_filter in "Users":
        right_y_axis_value = 0

    # Create temp DF for Errors
    scenario_right_y_axis_temp_df = pd.DataFrame(columns=["LocalTime", right_y_axis_filter])

    if not scenario_right_y_axis_df.empty:
        # Start Begin and End Time
        begin_time = scenario_right_y_axis_df["LocalTime"][scenario_right_y_axis_df.index[0]]
        end_time = scenario_right_y_axis_df["LocalTime"][scenario_right_y_axis_df.index[-1]]

        # Just get Divisor to know how many loops to go through
        loop_count = (end_time - begin_time) // granularity

        for i in range(loop_count):
            end_time = begin_time + granularity
            tmp_df = scenario_right_y_axis_df[
                (scenario_right_y_axis_df["LocalTime"] >= begin_time) &
                (scenario_right_y_axis_df["LocalTime"] <= end_time)]
            # Apply Filter - Users
            if right_y_axis_filter in "Users":
                right_y_axis_value = right_y_axis_value + tmp_df["Scenario"].count()
            # Apply Filter - Errors/RPS/RPM
            else:
                right_y_axis_value = tmp_df["Scenario"].count()

            # Add Value to the dataframe
            scenario_right_y_axis_temp_df.loc[i + 100000] = [begin_time, right_y_axis_value]

            begin_time = end_time

        # To calculate for the last TimeInterval
        end_time = scenario_right_y_axis_df["LocalTime"][scenario_right_y_axis_df.index[-1]]
        tmp_df = scenario_right_y_axis_df[(scenario_right_y_axis_df["LocalTime"] >= begin_time) &
                                          (scenario_right_y_axis_df["LocalTime"] <= end_time)]
        # Apply Filter - Users
        if right_y_axis_filter in "Users":
            right_y_axis_value = right_y_axis_value + tmp_df["Scenario"].count()
        # Apply Filter - Errors/RPS/RPM
        else:
            right_y_axis_value = tmp_df["Scenario"].count()

        # Fill the last value
        scenario_right_y_axis_temp_df.loc[-1] = [begin_time, right_y_axis_value]

    # Do a Rolling Mean for RPS - to remove the zig-zag Line
    if right_y_axis_filter in "RPS":
        scenario_right_y_axis_temp_df["RPS"] = scenario_right_y_axis_temp_df["RPS"].rolling(window=10).mean()
        scenario_right_y_axis_temp_df["RPS"] = scenario_right_y_axis_temp_df["RPS"].bfill()

    # Refresh the index
    scenario_right_y_axis_temp_df = scenario_right_y_axis_temp_df.reset_index(drop=True)
    scenario_right_y_axis_temp_df = scenario_right_y_axis_temp_df.applymap(str)

    return scenario_right_y_axis_temp_df


########################################################################################################################


########################################################################################################################
# Function Name: merge_right_y_axis_values_with_scenario_df
# Description  : Computes and merges the values of right y-axis to the given empty scenario df
# @param       : Empty Dataframe - empty_scenario_metrics_df
# @param       : Dataframe scenario_df, which is a filtered dataframe of gat_log_df based on given scenario.
#                Columns are: [Owner,Scenario, Transaction_Name, Status, ResponseTime, LocalTime]
# @param       : right_y_axis_filter_list values. As of now its limited to: Users, Errors, RPS and RPM
# @return      : Dataframe scenario_metrics_df with columns: [LocalTime, Users, Errors, RPS, RPM]
# Author       : Navdit Sharma
# Comments     : Created on 05/09/2018
########################################################################################################################
def merge_right_y_axis_values_with_scenario_df(empty_scenario_metrics_df: pd.DataFrame, scenario_df: pd.DataFrame,
                                               right_y_axis_filter: str) -> pd.DataFrame:
    # Errors
    if right_y_axis_filter in "Errors":
        # Errors DF
        scenario_errors_df = scenario_df.loc[scenario_df["Status"] == "KO"]
        # Compute values of the right y-axis
        scenario_errors_temp_df = compute_right_y_axis(scenario_errors_df, right_y_axis_filter, 1000)
        # Merge the dataframe of Errors
        empty_scenario_metrics_df = \
            empty_scenario_metrics_df.merge(scenario_errors_temp_df, on='LocalTime', how='outer')

    # Active Users
    elif right_y_axis_filter in "Users":
        # Active Users DF
        scenario_users_df = scenario_df.loc[scenario_df["Owner"] == "USER"]
        # Compute values of the right y-axis
        scenario_users_temp_df = compute_right_y_axis(scenario_users_df, right_y_axis_filter, 1000)
        # Merge the dataframe of Users
        empty_scenario_metrics_df = \
            empty_scenario_metrics_df.merge(scenario_users_temp_df, on='LocalTime', how='outer')

    # RPS
    elif right_y_axis_filter in ("RPS", "RPM"):
        # RPS DF
        scenario_rps_df = scenario_df.loc[scenario_df["Owner"] == "REQUEST"]
        # Compute values of the right y-axis
        if right_y_axis_filter in "RPS":
            scenario_users_temp_df = compute_right_y_axis(scenario_rps_df, right_y_axis_filter, 1000)
        else:
            scenario_users_temp_df = compute_right_y_axis(scenario_rps_df, right_y_axis_filter, 60000)
        # Merge the dataframe of Users
        empty_scenario_metrics_df = \
            empty_scenario_metrics_df.merge(scenario_users_temp_df, on='LocalTime', how='outer')

    # Return the filled_scenario_metrics_df (Just to remove confusion this step is there)
    filled_scenario_metrics_df = empty_scenario_metrics_df

    return filled_scenario_metrics_df


########################################################################################################################


########################################################################################################################
# Function Name: calculate_and_merge_transaction_percentiles
# Description  : Calculates the overall and interval based percentile of the given scenario
# @param       : Scenario Dataframe, which we got after filtering gat_log_df. Columns are : [Owner,Scenario,Transaction_
#                Name,Status,ResponseTime, LocalTime]
# @param       : Dataframe scenario_metrics_df, which have right-y-axis values merged. Columns are: [LocalTime,
#                ${right-y-axis-filter}]
# @param       : Percentile, which needs to be calculated for the scenario.
# @return      : Dataframe scenario_metrics_df with columns: [LocalTime, ${right-y-axis-filter}, ${TransactionNames}]
# @return      : Dataframe overall_transaction_percentile_df with columns: [Transaction, Percentile]
# Author       : Navdit Sharma
# Comments     : Created on 05/09/2018
########################################################################################################################
def calculate_and_merge_transaction_percentiles(scenario_df: pd.DataFrame,
                                                scenario_metrics_df: pd.DataFrame,
                                                percentile: int) -> (pd.DataFrame, pd.DataFrame):
    # Divide the percentile to get in the format, which will be given to Dataframe
    percentile = percentile / 100

    # Transactions OK DF
    scenario_ok_df = scenario_df.loc[scenario_df["Status"] == "OK"]

    # Overall Percentile
    overall_transaction_percentile_df = pd.DataFrame(columns=["Transaction", "Percentile"])

    # Get the transaction list in the scenario
    transactions_list = scenario_ok_df.Transaction_Name.unique().tolist()

    # for i in range(len(scenario_list)):
    for transaction_index in range(len(transactions_list)):
        transaction_name = transactions_list[transaction_index]

        # Make DF for transaction
        temp_df = pd.DataFrame(columns=["LocalTime", "TransactionName"])

        # Create new Transaction Dataframe
        transaction_df = scenario_ok_df[scenario_ok_df['Transaction_Name'] == transaction_name]

        # Calculate the overall Percentile of the Transaction
        overall_transaction_percentile_df.loc[transaction_index] = \
            [transaction_name, transaction_df.ResponseTime.quantile(percentile)]

        # Start Begin and End Time
        begin_time = transaction_df["LocalTime"][transaction_df.index[0]]
        end_time = transaction_df["LocalTime"][transaction_df.index[-1]]

        # Just get Divisor
        loop_count = (end_time - begin_time) // 1000

        for i in range(loop_count):
            end_time = begin_time + 1000
            tmp_df = transaction_df[
                (transaction_df["LocalTime"] >= begin_time) & (transaction_df["LocalTime"] <= end_time)]
            temp_df.loc[i + 100000] = [begin_time, tmp_df.ResponseTime.quantile(percentile)]
            begin_time = end_time

        # To calculate for the last TimeInterval
        end_time = transaction_df["LocalTime"][transaction_df.index[-1]]
        tmp_df = transaction_df[(transaction_df["LocalTime"] >= begin_time) & (transaction_df["LocalTime"] <= end_time)]
        temp_df.loc[-1] = [begin_time, tmp_df.ResponseTime.quantile(percentile)]

        # Clean the Dataframe from NaN values
        temp_df = temp_df.dropna(how='any')

        # Round the Percentile Column
        temp_df.TransactionName = temp_df.TransactionName.round(2)

        # Refresh the index
        temp_df = temp_df.reset_index(drop=True)

        # Rename the columns and set datatype to str of all values
        temp_df.rename(columns={'TransactionName': transaction_name}, inplace=True)
        temp_df = temp_df.applymap(str)

        # Join two Dataframes
        scenario_metrics_df = scenario_metrics_df.merge(temp_df, on='LocalTime', how='outer')

    return scenario_metrics_df, overall_transaction_percentile_df


########################################################################################################################


########################################################################################################################
# Function Name: get_scenario_metrics
# Description  : Calculates the Errors, Percentile of the given scenario
# @param       : Scenario Name
# @param       : Gatling Log Dataframe
# @param       : right_y_axis_filter value. As of now its limited to: Users, Errors, RPS and RPM
# @param       : percentile
# @return      : Dataframe scenario_metrics_df with columns: [LocalTime, Errors, ${TransactionNames}]
# @return      : Dataframe overall_transaction_percentile_df with columns: [Transaction, Percentile]
# Author       : Navdit Sharma
# Comments     : Created on 05/09/2018
########################################################################################################################
def get_scenario_metrics(scenario_name: str, gatling_log_df: pd.DataFrame,
                         right_y_axis_filter: str, percentile: int) -> (pd.DataFrame, pd.DataFrame):
    # Create new Scenario Dataframe
    cond_col = gatling_log_df['Scenario'] == scenario_name
    scenario_temp_df = gatling_log_df[cond_col]

    # New Dataframe
    scenario_metrics_df = pd.DataFrame(columns=["LocalTime"])

    # Calculate and Merge Right-Y-Axis Values
    scenario_metrics_df = merge_right_y_axis_values_with_scenario_df(scenario_metrics_df,
                                                                     scenario_temp_df, right_y_axis_filter)

    # Calculate and Merge Left-Y-Axis Values and get overall Percentile values.
    scenario_metrics_df, overall_transaction_percentile_df = calculate_and_merge_transaction_percentiles(
        scenario_temp_df, scenario_metrics_df, percentile)

    # Changing LocalTime to DateTime and sort the Time in Ascending order
    scenario_metrics_df['LocalTime'] = pd.to_datetime(scenario_metrics_df['LocalTime'], unit='ms')
    scenario_metrics_df = scenario_metrics_df.sort_values("LocalTime", ascending=True)

    # Add the Steady State Users which are not filled -- This is for smoothing of graph.
    if right_y_axis_filter not in "Errors":
        scenario_metrics_df[right_y_axis_filter] = scenario_metrics_df[right_y_axis_filter].astype(float)
        scenario_metrics_df[right_y_axis_filter] = scenario_metrics_df[right_y_axis_filter].interpolate().round(3)
        scenario_metrics_df[right_y_axis_filter] = scenario_metrics_df[right_y_axis_filter].astype(str)

    # Fill NaN values with zero
    scenario_metrics_df = scenario_metrics_df.fillna(0)

    # Return Two Dataframes
    return scenario_metrics_df, overall_transaction_percentile_df


########################################################################################################################


########################################################################################################################
# Function Name: check_path
# Description  : Take the location of file/directory and check if it exists. Else throw the exception.
# @param       : Path to be checked
# Author       : Navdit Sharma
# Comments     : Created on 05/09/2018
########################################################################################################################
def check_path(input_path: Path):
    if input_path.exists() is False:
        sys.exit("File doesn't exist. Please check path {}".format(input_path))
    elif str(input_path) in ".":
        return False


########################################################################################################################


########################################################################################################################
# Function Name: check_logs_path
# Description  : Checks the path of the log files.
# @param       : List of Log Paths
# @return      : List of Simulations logs.
# Author       : Navdit Sharma
# Comments     : Created on 05/09/2018
########################################################################################################################
def check_logs_path(input_logs_list: list) -> list:
    # Check if location of at least one Simulation Log has been provided.
    if not input_logs_list:
        sys.exit("Please provide location of at least one simulation log file as input to argument -i")

    # Split the given log files
    simulation_logs_list = strip_list(input_logs_list.split(','))

    # Loop through the given log files
    for logs in simulation_logs_list:
        file_loc = Path(logs)

        # Save result
        result = check_path(file_loc)

        # Check if any spaces have been given after the ,
        if result is False:
            sys.exit("While giving list of Gatling Log Files, "
                     "please don't leave any space before or after ','."
                     "\nCurrent Input looks like - {}".format(input_logs_list))

    return simulation_logs_list


########################################################################################################################


########################################################################################################################
# Function Name: strip_list
# Description  : Take a list of string objects and return the same list stripped of extra whitespace.
# @param       : List which needs to be stripped of the extra white spaces
# @return      : The same list, which was given as input but stripped of whitespaces
# Author       : Navdit Sharma
# Comments     : Created on 05/09/2018
########################################################################################################################
def strip_list(list_input: list) -> list:
    return [x.strip() for x in list_input]


########################################################################################################################


########################################################################################################################
# Function Name: validate_user_given_arguments
# Description  : Validates the input given by the user to the python script
# @param       : Arguments given by user
# @return      : List of the Simulation Log Files
# @return      : If given, path of the Graph, where the user wants to get generated
# Author       : Navdit Sharma
# Comments     : Created on 05/09/2018
########################################################################################################################
def validate_user_given_arguments(argv):
    # Arguments
    version = '1.0'
    verbose = False
    output_graph_path = 'GatlingScenarioGraphs.html'
    input_log = ""
    input_percentile = 95

    # print('ARGV      : {}'.format(sys.argv[1:]))

    options, remainder = getopt.getopt(sys.argv[1:], 'i:p:o:v', ['input=',
                                                                 'output=',
                                                                 'percentile='
                                                                 'verbose',
                                                                 'version=',
                                                                 ])
    # print('OPTIONS   : {}'.format(options))

    for opt, arg in options:
        if opt in ('-o', '--output_graph'):
            output_graph_path = arg
        elif opt in ('-i', '--simulation_log'):
            input_log = arg
        elif opt in ('-p', '--percentile'):
            input_percentile = arg
        elif opt in ('-v', '--verbose'):
            verbose = True
        elif opt == '--version':
            version = arg

    # print('VERSION   : {}'.format(version))
    # print('VERBOSE   : {}'.format(verbose))
    # print('OUTPUT    : {}'.format(output_graph_path))
    # print('LOG FILES : {}'.format(input_log))
    # print('REMAINING : {}'.format(remainder))

    return input_log, output_graph_path, input_percentile


########################################################################################################################


########################################################################################################################
# Function Name: get_list_of_scenarios
# Description  : Gives the sorted list of the scenarios, which were run in the Gatling Test
# @param       : Gatling Log Dataframe
# @return      : Sorted List of Scenarios
# Author       : Navdit Sharma
# Comments     : Created on 20/09/2018
########################################################################################################################
def get_list_of_scenarios(gatling_log_df: pd.DataFrame) -> list:
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
# @param       : Scenario Metrics Dataframe and Overall Percentile Dataframe.
# @return      : Dictionary of Column Names
# Author       : Navdit Sharma
# Comments     : Created on 05/09/2018
########################################################################################################################
def remove_dollar_sign_and_get_column_names_dict(scenario_metrics_df: pd.DataFrame,
                                                 overall_percentile_df: pd.DataFrame) -> dict:
    col_name_dict = {}
    for column in scenario_metrics_df:
        new_col_name = column.replace("$", "")
        scenario_metrics_df.rename(columns={column: new_col_name}, inplace=True)
        overall_percentile_df['Transaction'] = \
            overall_percentile_df['Transaction'].replace(column, new_col_name)
        col_name_dict[new_col_name] = column

    return col_name_dict


########################################################################################################################


########################################################################################################################
# Function Name: get_y_range_of_graph
# Description  : Gives the Right and Left Y-axis range of the graph based on the max value in dataframe
# @param       : Scenario Metrics Dataframe
# @param       : right_y_axis_filters_list - List of rigth y-Axis filters
# @return      : Left and Right Y-Axis Range of Bokeh Graph
# Author       : Navdit Sharma
# Comments     : Created on 05/09/2018
########################################################################################################################
def get_y_range_of_graph(scenario_metrics_df: pd.DataFrame, right_y_axis_filter: str) -> (int, int):
    tmp_max_val_df = scenario_metrics_df
    tmp_max_val_df = tmp_max_val_df.apply(pd.to_numeric)

    # Right y-Axis Range
    right_y_axis_range = tmp_max_val_df[right_y_axis_filter].max() + 1

    # Left y-axis Range
    tmp_max_val_df = tmp_max_val_df.drop(["LocalTime"], axis=1)

    # Drop Right-Y-Axis Columns
    tmp_max_val_df = tmp_max_val_df.drop([right_y_axis_filter], axis=1)

    left_y_axis_range = (0, tmp_max_val_df.values.max() + 50)

    return left_y_axis_range, right_y_axis_range


########################################################################################################################


########################################################################################################################
# Function Name: get_color_palette
# Description  : To set the color palette, which will be used in plotting Bokeh Graph
# @param       : Scenario Metrics Dataframe
# @param       : Scenario Name, for which the Color Palette has to be set
# @return      : Color Palette
# Author       : Navdit Sharma
# Comments     : Created on 05/09/2018
########################################################################################################################
def get_color_palette(scenario_metrics_df: pd.DataFrame, scenario: str) -> list:
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
# Author       : Navdit Sharma
# Comments     : Created on 05/09/2018
########################################################################################################################
def set_hover_tool_tips() -> object:
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
# @param       : x_axis_label - Label of X-Axis
# @param       : x_axis_type
# @param       : y_axis_label - Label of Y-Axis
# @param       : plot_width - Width of the graph to be plotted
# @param       : plot_height - Height of the graph to be plotted
# @param       : left_y_range - Range of Y-Axis
# @param       : toolbar_location - Location of Bokeh Toolbar
# @param       : tools_to_show - Bokeh tools, which you would like to show on graph
# @return      : figure
# Author       : Navdit Sharma
# Comments     : Created on 05/09/2018
########################################################################################################################
def plot_new_graph(x_axis_label: str, x_axis_type: str, y_axis_label: str, plot_width: int, plot_height: int,
                   left_y_range: int, toolbar_location: str, tools_to_show: str) -> figure():
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
# Author       : Navdit Sharma
# Comments     : Created on 05/09/2018
########################################################################################################################
def set_graph_and_legend_properties(plot_graph: figure(), legends: list, scenario: str) -> figure():
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
# Function Name: sort_transaction_names_and_remove_localtime_col
# Description  : Sorts the transactions names in Alphabetical order and removes Localtime Column
# @param       : Right Y-Axis Filter
# @param       : List of Column Names
# @param       : Sort -- True, if you want to sort the column names. Else the Legend will have the order of
#                transactions in which they were executed. Default value is True.
# @return      : List of Column Names, in the order in which they will be plotted and shown on Legend
# Author       : Navdit Sharma
# Comments     : Created on 05/09/2018
########################################################################################################################
def sort_transaction_names_and_remove_localtime_col(right_y_axis_filter: str,
                                                    col_list: list, sort: bool = True) -> list:
    if sort:
        # Remove the right y axis filter
        col_list.remove(right_y_axis_filter)
        # Remove LocalTime
        col_list.remove("LocalTime")
        # Sort the List
        col_list.sort()
        # Insert Right Y axis Filter in the beginning so that its always on top in Legend
        col_list.insert(0, right_y_axis_filter)
    else:
        # Remove LocalTime
        col_list.remove("LocalTime")

    return col_list


########################################################################################################################


########################################################################################################################
# Function Name: plot_graph_by_transaction
# Description  : Plots the graph of all the transactions in a given scenario
# @param       : scenario_graph Figure
# @param       : Right Y-Axis Filter
# @param       : Percentile
# @return      : Figure of Plotted graph along with Legend in Legend List
# Author       : Navdit Sharma
# Comments     : Created on 05/09/2018
########################################################################################################################
def plot_graph_by_transaction(scenario_metrics_df: pd.DataFrame, overall_percentile_df: pd.DataFrame, scenario: str,
                              right_y_axis_filter: str, percentile: int) -> figure():
    # Remove $ from the names of column names of scenario_metrics_df and
    # Rename the Transactions of overall_percentile_df
    col_name_dict = remove_dollar_sign_and_get_column_names_dict(scenario_metrics_df, overall_percentile_df)

    # Define Y-Axis Range of the Graph
    (left_y_range, right_y_range) = get_y_range_of_graph(scenario_metrics_df, right_y_axis_filter)

    # Get the colors for the Lines of the Graph
    color_palette = get_color_palette(scenario_metrics_df, scenario)

    # Tools to be available in graph
    tools_to_show = 'box_zoom,reset,save'

    # create a new plot with a title and axis labels
    scenario_graph = plot_new_graph('Time', 'datetime', 'Response Time (ms)', 1900, 400, left_y_range, 'below',
                                    tools_to_show)

    # Disabling Hover Tool
    scenario_graph.toolbar.active_inspect = None

    # Index to go through Color Palette
    color_index = 0

    # get all the legends in one list
    legend_list = []

    # Sort the Transactions names in Alphabetical order
    transaction_col_list = sort_transaction_names_and_remove_localtime_col(right_y_axis_filter,
                                                                           list(scenario_metrics_df.columns))

    # Source of Graphs
    source = ColumnDataSource(scenario_metrics_df)

    # Plot graph transaction-wise
    for col_name in transaction_col_list:
        if col_name in right_y_axis_filter:
            # Get the legend name
            legend_name = col_name

            # Setting the second y axis range name and range
            scenario_graph.extra_y_ranges = {col_name: Range1d(0, right_y_range)}

            # Adding the second axis to the plot.
            scenario_graph.add_layout(LinearAxis(y_range_name=col_name, axis_label=col_name), 'right')

            # PlotGraph
            if col_name in "Errors":
                axis_color = "#d62728"
            else:
                axis_color = "yellow"
            plot_graph = scenario_graph.line('LocalTime',
                                             col_name,
                                             source=source,
                                             line_width=2,
                                             color=axis_color,
                                             y_range_name=col_name,
                                             name=col_name)

        else:
            # Transaction Percentile
            col_percentile = int(overall_percentile_df.loc
                                 [overall_percentile_df['Transaction'] == col_name, 'Percentile'].item())

            # Get the legend name along with Transaction's Percentile
            legend_name = col_name_dict[col_name] + " ({}th: {} ms)".format(percentile, col_percentile)

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
# @param       : right y-axis filter. Currently, they are limited to [Errors, Users, RPS, RPM]
# @param       : Percentile, for which graph needs to be produced. Default Value is 95
# @return      : Layout of the graph
# Author       : Navdit Sharma
# Comments     : Created on 05/09/2018
########################################################################################################################
def generate_graph(gat_log_df: pd.DataFrame, graph_output_path: str, right_y_axis_filter: str,
                   percentile: int) -> object:
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

        # Get scenario_metrics_df and overall_percentile_df
        (scenario_metrics_df, overall_percentile_df) = get_scenario_metrics(scenario_name,
                                                                            gat_log_df,
                                                                            right_y_axis_filter,
                                                                            percentile)

        # Plot Graphs of the Transactions in Scenario
        complete_scenario_graph = plot_graph_by_transaction(scenario_metrics_df, overall_percentile_df,
                                                            scenario_name, right_y_axis_filter, percentile)

        # Add the Scenario Graphs to the Final Combined Graph
        scenario_plots.append(complete_scenario_graph)

        print("{} Completed.".format(scenario_name))

    # put all the plots in a Column
    layout = Column(children=scenario_plots)

    # Return the layout
    return layout


########################################################################################################################


########################################################################################################################
# Function Name: main
# Description  : Calls the functions to consume Excel given by the user and update the scenarios
# @param       : Null
# @return      : Null
# Author       : Navdit Sharma
# Comments     : Created on 05/09/2018
########################################################################################################################
def main(argv):
    # Get the Log Files Location and Output Graph Location
    simulation_logs, output_graph, percentile = validate_user_given_arguments(argv)

    # Check if Log Files Exist
    simulation_logs_list = check_logs_path(simulation_logs)

    # Generate Combined Gatling Log Dataframe
    gat_log_graph_df = generate_gatling_log_df(simulation_logs_list)

    # Generate Graph
    right_y_axis_filter_list = ["RPS", "Users", "Errors"]

    # Initialise an Empty Tab List
    tab_list = []

    # Looping through the right-y-axis Filters
    for right_y_axis_filter in right_y_axis_filter_list:
        print("-- {}th vs {} Graph Started --".format(percentile, right_y_axis_filter))

        # Get the graph
        graph_layout = generate_graph(gat_log_graph_df, output_graph, right_y_axis_filter, percentile)

        # Add the Graph to the layout
        tab = Panel(child=graph_layout, title="{}th vs {}".format(percentile, right_y_axis_filter))

        # Append the Tab to the Tab list
        tab_list.append(tab)

        print("-- {}th vs {} Graph Completed --".format(percentile, right_y_axis_filter))

    # Get the Final HTML Page Ready
    tabs = Tabs(tabs=tab_list)

    # Save/Show HTML File
    save(tabs)

##################################################################################################################


##################################################################################################################
# Function Name: __main__
# Description  : Entry Point of the script
# @param       : Null
# @return      : Null
# Author       : Navdit Sharma
# Comments     : Created on 05/09/2018
##################################################################################################################
if __name__ == "__main__":
    print("Script Started")
    # Start Time of Code
    start_time = time.time()

    # Call the main function
    main(sys.argv[1:])

    # Print Time taken to execute script
    print("CUSTOM INFO : --- Script Execution Time: %s seconds ---" % (time.time() - start_time))

##################################################################################################################
