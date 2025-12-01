import numpy as np
import pandas as pd
import glob2
import os
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import MinMaxScaler
import joblib


""" 
Data_clean is a module for cleaning and preparing data for analysis. it includes functions to combine multiple CSV files,
clean the data, normalize specified columns, and split the data into training and testing sets.
######################################### NOTE ##################################################################################
This module contains functions for cleaning and preparing data for analysis. 
It is assumed that the input data is in CSV format with consistent structure across files.
There should be a folder with input play CSV files for processing, and a seperate folder with 
output play CSV files for processing. The functions below will read these files, clean the data,
and prepare them for further analysis or modeling.
"""

def combine_data(input_path: str, output_path: str, drop_duplicates: bool=True, return_cv: bool=False) -> pd.DataFrame:
    """
    Cleans data from a list of CSV files. Combines into a single DataFrame.
    Parameters: 
    cv_list (list): List of CSV file paths.
    combine (bool): Whether to combine all data into a single DataFrame.    
    Returns: df_combined (DataFrame): Combined cleaned DataFrame if combine is True.
    """
    # Get sorted list of input and output csv files to ensure order is preserved
    input_files = sorted(glob.glob(os.path.join(input_path, "*.csv")))
    output_files = sorted(glob.glob(os.path.join(output_path, "*.csv")))

    # Load and concatenate input files (vertically)
    df_inputs = pd.concat([pd.read_csv(f) for f in input_files], axis=0, ignore_index=True)

    # Load and concatenate output files (vertically)
    df_outputs = pd.concat([pd.read_csv(f) for f in output_files], axis=0, ignore_index=True)
    # Change output column names to avoid conflicts x, y -> x', y'
    df_outputs = df_outputs.rename(columns={'x': "x'", 'y': "y'"})
    
    # Combine input and output dataframes column-wise (axis=1)
    df_combined = pd.concat([df_inputs, df_outputs], axis=1)
    return df_combined, df_inputs, df_outputs

def cleaned_data(df: pd.DataFrame, 
                 columns: list) -> pd.DataFrame:
    """ 
    Just returns data frame with positions x, y, x', y' and given columns
    one-hot encods categorical variables i.e. player_position, player_side, player_role
    Parameters:
    df (DataFrame): The input DataFrame.
    columns (list): List of columns to include in the returned DataFrame.
    e.g., ['game_id', 'play_id', 'player_to_predict', 'nfl_id', 'frame_id', 'play_direction', 
    'absolute_yardline_number', 'player_name', 'player_height', 'player_weight', 'player_birth_date', 
    'player_position', 'player_side', 'player_role', 'x', 'y', 's', 'a', 'dir', 'o', 'num_frames_output', 
    'ball_land_x', 'ball_land_y']
    Returns:
    DataFrame: A DataFrame containing only the specified columns.
    """
    selected_columns = ['x', 'y', "x'", "y'"] + columns
    cleaned_df = df[selected_columns].copy()
    # One-hot encode categorical variables
    if 'player_side' in cleaned_df.columns:
        # One-hot encode 'player_side'
        onehot = pd.get_dummies(cleaned_df['player_side'])
        # Ensure column order: offense first, defense second
        onehot = onehot[['offense', 'defense']]
        cleaned_df = pd.concat([cleaned_df.drop('player_side', axis=1), onehot], axis=1)
    if 'player_position' in cleaned_df.columns:
        # One-hot encode 'player_position'
        onehot = pd.get_dummies(cleaned_df['player_position'], prefix='position')
        cleaned_df = pd.concat([cleaned_df.drop('player_position', axis=1), onehot], axis=1)    
    if 'player_role' in cleaned_df.columns:
        # One-hot encode 'player_role'
        onehot = pd.get_dummies(cleaned_df['player_role'], prefix='role')
        cleaned_df = pd.concat([cleaned_df.drop('player_role', axis=1), onehot], axis=1)
    
    return cleaned_df

def normalize_data(df: pd.DataFrame, columns_to_normalize: list) -> tuple: 
    """
    Normalizes specified columns in the DataFrame using min-max scaling.
    Parameters:
    df (DataFrame): The input DataFrame.
    columns_to_normalize (list): List of column names to normalize.
    Returns:
    tuple: Normalized feature and target DataFrames, and the fitted scalers.
    x_scaler, y_scaler
    DataFrame: A DataFrame with normalized columns.
    """
    df_normalized = df.copy()

    # Identify features and target
    X = df_normalized[['x', 'y'] + columns_to_normalize]
    Y = df_normalized[["x'", "y'"]]

    #normalize data
    xscaler = MinMaxScaler()
    yscaler = MinMaxScaler()

    x_norm = xscaler.fit_transform(X)
    y_norm = yscaler.fit_transform(Y)
    #x_norm = pd.DataFrame(x_norm, columns=['x', 'y'] + columns_to_normalize)
    #y_norm = pd.DataFrame(y_norm, columns=["x'", "y'"])
    joblib.dump(xscaler, 'xscaler.save')
    joblib.dump(yscaler, 'yscaler.save')
    return x_norm, y_norm, xscaler, yscaler

def data_split(x_norm: pd.DataFrame, y_norm: pd.DataFrame, test_size: float=0.2) -> tuple:
    """
    Splits DataFrame into training and testing sets.
    Parameters:
    df (DataFrame): The DataFrame to split.
    test_size (float): Proportion of the dataset to include in the test split.
    random_state (int): Random seed for reproducibility.
    Returns: X_train, X_test, Y_train, Y_test
    4 DataFrames corresponding to training and testing sets.
    """
    X_train, X_test, Y_train, Y_test = train_test_split(x_norm, y_norm, test_size=test_size, random_state=42)
    return X_train, X_test, Y_train, Y_test

def data_clean(input_path: str, output_path: str, drop_duplicates: bool=True,  
        columns: list=[], columns_to_normalize: list=[], test_size: float=0.2) -> tuple:
    """
    Full data cleaning pipeline that combines, cleans, normalizes, and splits the data.
    Parameters:
    input_path (str): Path to the folder containing input CSV files.
    output_path (str): Path to the folder containing output CSV files.
    drop_duplicates (bool): Whether to drop duplicate rows.
    columns (list): List of columns to include in the cleaned DataFrame.
    columns_to_normalize (list): List of columns to normalize.
    test_size (float): Proportion of the dataset to include in the test split.
    Returns:
    tuple: X_train, X_test, Y_train, Y_test, xscaler, yscaler
    4 DataFrames for training and testing sets, and the fitted scalers.
    """
    # Combine data
    df_combined, df_inputs, df_outputs = combine_data(input_path, output_path, drop_duplicates)
    # Clean data
    cleaned_df = cleaned_data(df_combined, columns)
    # Normalize data
    x_norm, y_norm, xscaler, yscaler = normalize_data(cleaned_df, columns_to_normalize)
    # Split data
    X_train, X_test, Y_train, Y_test = data_split(x_norm, y_norm, test_size)
    return X_train, X_test, Y_train, Y_test, xscaler, yscaler