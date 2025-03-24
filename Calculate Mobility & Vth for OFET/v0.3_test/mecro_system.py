import os
import pandas as pd
import math


class ActionFile:
    def __init__(self, open_file_path, result_file_path):
        self.open_file_path = open_file_path
        self.result_file_path = result_file_path

    def start(self, L, W, C, FV, point_count, is_n_type):
        df = self.read_csv()
        results = self.process_data(df, W, L, C, FV, point_count, is_n_type)
        self.write_results(results)

    def read_csv(self):
        """Read CSV file into a DataFrame."""
        return pd.read_csv(self.open_file_path)

    def process_data(self, df, W, L, C, FV, point_count, is_n_type):
        results = []
        df['absID'] = df['ID'].abs()
        df['absIG'] = df['IG'].abs()
        df['sqrtID'] = df['absID'].apply(math.sqrt)

        for index, row in df.iterrows():
            vg = row['VG']
            if (is_n_type and vg >= FV) or (not is_n_type and vg <= FV):
                slope, intercept_x, intercept_y = self.calculate_slope(df, index, point_count)
                mobility = (slope ** 2) * ((2 * L) / W) * (1 / C)
                results.append([row['file_name'], slope, intercept_y, intercept_x, mobility, W, L, C])

        return results

    def calculate_slope(self, df, index, point_count):
        """Calculate slope and intercepts."""
        relevant_data = df.iloc[max(0, index - point_count + 1):index + 1]  # Include current point
        avg_x = relevant_data['VG'].mean()
        avg_y = relevant_data['sqrtID'].mean()

        slope = ((relevant_data['VG'] - avg_x) * (relevant_data['sqrtID'] - avg_y)).sum() / \
                 ((relevant_data['VG'] - avg_x) ** 2).sum()
        intercept_y = avg_y - slope * avg_x
        intercept_x = -intercept_y / slope

        return slope, intercept_x, intercept_y

    def write_results(self, results):
        """Write results to a CSV file."""
        columns = ['file_name', 'slope', 'intercept', 'Vth', 'mobility', 'Width', 'Length', 'Capacitance']
        result_df = pd.DataFrame(results, columns=columns)
        result_df.to_csv(self.result_file_path, index=False)


class System:
    def __init__(self, main):
        self.L = 100
        self.W = 1000
        self.C = 4.44E-08
        self.FV = -40
        self.point_count = 5
        self.is_n_type = False
        self.main = main

    def start(self, folder_path, result_folder_path):
        """Process all CSV files in the given folder."""
        try:
            csv_files = [f for f in os.listdir(folder_path) if f.endswith('.csv')]
            for file_name in csv_files:
                action_file = ActionFile(os.path.join(folder_path, file_name),
                                          os.path.join(result_folder_path, file_name))
                action_file.start(self.L, self.W, self.C, self.FV, self.point_count, self.is_n_type)
            self.create_result_list_file(result_folder_path)
            return True
        except Exception as e:
            print(e)
            self.main.error(str(e))
            return False

    def create_result_list_file(self, result_folder_path):
        """Combine results from all processed files into a single CSV file."""
        combined_results = []
        for file_name in os.listdir(result_folder_path):
            if file_name.endswith('.csv'):
                df = pd.read_csv(os.path.join(result_folder_path, file_name))
                combined_results.append(df)

        result_df = pd.concat(combined_results, ignore_index=True)
        result_df.to_csv(os.path.join(result_folder_path, 'mobility.csv'), index=False)

    def set_params(self, W=None, L=None, C=None, FV=None, point_count=None, is_n_type=None):
        """Set parameters for calculations."""
        if W is not None: self.W = W
        if L is not None: self.L = L
        if C is not None: self.C = C
        if FV is not None: self.FV = FV
        if point_count is not None: self.point_count = point_count
        if is_n_type is not None: self.is_n_type = is_n_type
