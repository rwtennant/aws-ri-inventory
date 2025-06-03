from datetime import datetime
from datetime import timedelta
import boto3
import pandas as pd
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import functools as ft
import threading

# Global variables to store data
df_results = None
progress_var = None
progress_bar = None
mainApp = None

def create_aws_session(input_access_key_id, input_secret_access_key, input_session_token):
    aws_session = boto3.Session(
        aws_access_key_id=input_access_key_id,
        aws_secret_access_key=input_secret_access_key,
        aws_session_token=input_session_token
    )
    return aws_session

def get_ris(session):
    global progress_var
    if progress_var:
        progress_var.set("Getting RI Inventory...")
    print("Getting RI Inventory")
    
    regions_to_check = ["ca-central-1", "eu-west-1", "us-west-2", "ap-northeast-1"]
    ris = []
    
    for region in regions_to_check:
        print(region)
        try:
            ec2_client = session.client("ec2", region_name=region)
            ris_response = ec2_client.describe_reserved_instances()
            
            for ri in ris_response["ReservedInstances"]:
                ri_dict = {}
                ri_dict["ReservedInstancesId"] = ri["ReservedInstancesId"]
                ri_dict["Start"] = ri["Start"].strftime('%Y-%m-%d %H:%M:%S')
                ri_dict["End"] = ri["End"].strftime('%Y-%m-%d %H:%M:%S')
                ri_dict["State"] = ri["State"]
                ri_dict["Region"] = region
                ri_dict["InstanceType"] = ri["InstanceType"]
                ris.append(ri_dict)
        except Exception as e:
            print(f"Error in region {region}: {e}")
    
    return pd.DataFrame(ris)

def get_ri_listings(session):
    global progress_var
    if progress_var:
        progress_var.set("Getting RI Listings...")
    print("Getting RI Listings")
    
    regions_to_check = ["ca-central-1", "eu-west-1", "us-west-2", "ap-northeast-1"]
    ri_listings = []
    
    for region in regions_to_check:
        print(region)
        try:
            ec2_client = session.client("ec2", region_name=region)
            ri_listings_response = ec2_client.describe_reserved_instances_listings()
            ri_listings_json_list = ri_listings_response["ReservedInstancesListings"]
            
            for ri_listing in ri_listings_json_list:
                ri_listed_date = ri_listing["CreateDate"]
                
                if ri_listing["Status"] == "active":
                    ri_sale_or_current_date = datetime.today()
                else:
                    ri_sale_or_current_date = ri_listing["UpdateDate"]
                
                days_on_marketplace = ri_sale_or_current_date.date() - ri_listed_date.date()
                
                ri_listing_dict = {}
                ri_listing_dict["ClientToken"] = ri_listing["ClientToken"]
                ri_listing_dict["ReservedInstancesListingId"] = ri_listing["ReservedInstancesListingId"]
                ri_listing_dict["ReservedInstancesId"] = ri_listing["ReservedInstancesId"]
                ri_listing_dict["ListingCreateDate"] = ri_listing["CreateDate"]
                ri_listing_dict["Term"] = ri_listing["PriceSchedules"][0]["Term"]
                ri_listing_dict["ListingStatus"] = ri_listing["Status"]
                ri_listing_dict["ListingUpdateDate"] = ri_listing["UpdateDate"]
                ri_listing_dict["DaysOnMarket"] = days_on_marketplace.days
                ri_listings.append(ri_listing_dict)
        except Exception as e:
            print(f"Error in region {region}: {e}")

    return pd.DataFrame.from_dict(ri_listings, orient="columns")

def get_ri_utilization(session):
    global progress_var
    if progress_var:
        progress_var.set("Getting RI Utilization...")
    print("Getting RI Utilization")

    ri_util_end_dt = datetime.today().date()
    ri_util_end_dt_str = ri_util_end_dt.strftime("%Y-%m-%d")
    ri_util_start_dt = ri_util_end_dt - timedelta(days=30)
    ri_util_start_dt_str = ri_util_start_dt.strftime("%Y-%m-%d")

    try:
        ce_client = session.client("ce")
        ri_utilization_response = ce_client.get_reservation_utilization(
            TimePeriod={
                "Start": ri_util_start_dt_str,
                "End": ri_util_end_dt_str
            },
            GroupBy=[
                {
                    "Type": "DIMENSION",
                    "Key": "SUBSCRIPTION_ID"
                }
            ]
        )
        ri_util_by_sub = ri_utilization_response["UtilizationsByTime"][0]["Groups"]

        ri_sub_utilization = []
        for sub in ri_util_by_sub:
            ri_sub_ri_ARN = sub["Attributes"]["reservationARN"]
            ri_sub_ri_ID = ri_sub_ri_ARN.split("/")[1]

            ri_sub_util_dict = {}
            ri_sub_util_dict["ReservedInstancesId"] = ri_sub_ri_ID
            ri_sub_util_dict["SubscriptionStatus"] = sub['Attributes']['subscriptionStatus']
            ri_sub_util_dict["TotalAssetValue"] = sub['Attributes']['totalAssetValue']
            ri_sub_util_dict["StartDateTime"] = sub['Attributes']['startDateTime']
            ri_sub_util_dict["EndDateTime"] = sub['Attributes']['endDateTime']
            ri_sub_util_dict["UtilizationPercentage"] = sub['Utilization']['UtilizationPercentage']
            ri_sub_util_dict["UnusedHours"] = sub['Utilization']['UnusedHours']
            ri_sub_util_dict["NetRISavings"] = sub['Utilization']['NetRISavings']

            ri_sub_utilization.append(ri_sub_util_dict)        

        return pd.DataFrame.from_dict(ri_sub_utilization, orient="columns")
    except Exception as e:
        print(f"Error getting utilization: {e}")
        return pd.DataFrame()

def join_ri_util_listings(ri_df_list):
    if progress_var:
        progress_var.set("Merging data...")
    df_ri_list = ft.reduce(lambda left,right: pd.merge(left,right,on=['ReservedInstancesId'], how='outer'), ri_df_list)
    return df_ri_list

def show_results_window():
    global df_results
    if df_results is None or df_results.empty:
        messagebox.showinfo("No Data", "No data to display")
        return
    
    # Clean the data - replace NaN and NaT values with empty strings
    df_display = df_results.copy()
    df_display = df_display.fillna('')
    
    # Create results window with clean styling
    results_window = tk.Toplevel(mainApp)
    results_window.title('Reserved Instance Data')
    results_window.geometry('1300x750')
    results_window.configure(bg='white')
    
    # Configure clean styling for results window
    style = ttk.Style()
    style.configure('Clean.TFrame', background='white')
    style.configure('Header.TLabel', font=('Arial', 14, 'bold'), background='white', foreground='#1a1a1a')
    style.configure('Info.TLabel', font=('Arial', 9), background='white', foreground='#666666')
    style.configure('Search.TEntry', fieldbackground='white', borderwidth=1, relief='solid', padding=6)
    style.configure('Clean.Treeview', font=('Arial', 9), rowheight=22)
    style.configure('Clean.Treeview.Heading', font=('Arial', 9, 'bold'), relief='flat')
    
    # Main container
    main_container = ttk.Frame(results_window, style='Clean.TFrame', padding="20")
    main_container.pack(fill='both', expand=True)
    
    # Header
    header_frame = ttk.Frame(main_container, style='Clean.TFrame')
    header_frame.pack(fill='x', pady=(0, 15))
    
    ttk.Label(
        header_frame,
        text="Reserved Instance Data",
        style='Header.TLabel'
    ).pack(side='left')
    
    info_label = ttk.Label(
        header_frame,
        text=f"{len(df_results)} records",
        style='Info.TLabel'
    )
    info_label.pack(side='right')
    
    # Search and filter
    search_frame = ttk.Frame(main_container, style='Clean.TFrame')
    search_frame.pack(fill='x', pady=(0, 15))
    
    ttk.Label(search_frame, text="Search:", font=('Arial', 9), background='white').pack(side='left', padx=(0, 8))
    search_var = tk.StringVar()
    search_entry = ttk.Entry(search_frame, textvariable=search_var, width=30, style='Search.TEntry')
    search_entry.pack(side='left', padx=(0, 20))
    
    if 'State' in df_display.columns:
        ttk.Label(search_frame, text="State:", font=('Arial', 9), background='white').pack(side='left', padx=(0, 8))
        state_filter = ttk.Combobox(search_frame, width=12, font=('Arial', 9))
        states = ['All'] + sorted(list(df_display['State'].dropna().unique()))
        state_filter['values'] = states
        state_filter.set('All')
        state_filter.pack(side='left')
    
    # Data table
    tree_frame = ttk.Frame(main_container, style='Clean.TFrame')
    tree_frame.pack(fill='both', expand=True, pady=(0, 15))
    
    # Create treeview
    columns = list(df_display.columns)
    tree = ttk.Treeview(
        tree_frame, 
        columns=columns, 
        show='headings',
        style='Clean.Treeview'
    )
    
    # Track sorting state
    sort_reverse = {col: False for col in columns}
    
    def sort_column(col):
        """Sort the treeview by the selected column"""
        data = []
        for child in tree.get_children():
            values = tree.item(child)['values']
            data.append(values)
        
        col_index = columns.index(col)
        
        def sort_key(row):
            val = row[col_index]
            if val == '' or val is None:
                return ('', 0)
            
            try:
                return ('num', float(val))
            except (ValueError, TypeError):
                pass
            
            try:
                return ('date', datetime.strptime(str(val), '%Y-%m-%d %H:%M:%S'))
            except (ValueError, TypeError):
                pass
            
            return ('str', str(val).lower())
        
        data.sort(key=sort_key, reverse=sort_reverse[col])
        sort_reverse[col] = not sort_reverse[col]
        
        for item in tree.get_children():
            tree.delete(item)
        
        for row in data:
            tree.insert('', 'end', values=row)
        
        direction = " ↓" if not sort_reverse[col] else " ↑"
        tree.heading(col, text=f"{col}{direction}")
        
        for other_col in columns:
            if other_col != col:
                tree.heading(other_col, text=other_col)
    
    # Configure columns
    for col in columns:
        tree.heading(col, text=col, command=lambda c=col: sort_column(c))
        tree.column(col, width=120, minwidth=80)
    
    # Scrollbars
    v_scrollbar = ttk.Scrollbar(tree_frame, orient='vertical', command=tree.yview)
    h_scrollbar = ttk.Scrollbar(tree_frame, orient='horizontal', command=tree.xview)
    tree.configure(yscrollcommand=v_scrollbar.set, xscrollcommand=h_scrollbar.set)
    
    v_scrollbar.pack(side='right', fill='y')
    h_scrollbar.pack(side='bottom', fill='x')
    tree.pack(side='left', fill='both', expand=True)
    
    # Population and filter functions
    def populate_tree(df_to_show):
        for item in tree.get_children():
            tree.delete(item)
        
        for index, row in df_to_show.iterrows():
            row_values = []
            for val in row:
                if pd.isna(val) or str(val).lower() in ['nan', 'nat', 'none']:
                    row_values.append('')
                else:
                    row_values.append(str(val))
            tree.insert('', 'end', values=row_values)
    
    def apply_filters(*args):
        filtered_df = df_display.copy()
        
        search_text = search_var.get().lower()
        if search_text:
            mask = filtered_df.astype(str).apply(lambda x: x.str.lower().str.contains(search_text, na=False)).any(axis=1)
            filtered_df = filtered_df[mask]
        
        if 'State' in df_display.columns:
            state_value = state_filter.get()
            if state_value and state_value != 'All':
                filtered_df = filtered_df[filtered_df['State'] == state_value]
        
        populate_tree(filtered_df)
        info_label.config(text=f"Showing {len(filtered_df)} of {len(df_results)} records")
    
    # Bind filters
    search_var.trace('w', apply_filters)
    if 'State' in df_display.columns:
        state_filter.bind('<<ComboboxSelected>>', apply_filters)
    
    # Initial population
    populate_tree(df_display)
    
    # Buttons
    button_frame = ttk.Frame(main_container, style='Clean.TFrame')
    button_frame.pack(fill='x')
    
    def export_csv():
        filename = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv")],
            title="Save CSV file"
        )
        if filename:
            df_export = df_results.copy()
            df_export = df_export.fillna('')
            df_export.to_csv(filename, index=False)
            messagebox.showinfo("Export Complete", f"Data exported to {filename}")
    
    ttk.Button(
        button_frame, 
        text="Export CSV", 
        command=export_csv,
        style='Primary.TButton'
    ).pack(side='left', padx=(0, 10))
    
    ttk.Button(
        button_frame, 
        text="Close", 
        command=results_window.destroy,
        style='Secondary.TButton'
    ).pack(side='right')

def create_ri_inventory_and_listings(input_access_key_id, input_secret_access_key, input_session_token):
    global df_results, progress_var, progress_bar
    
    try:
        # Start progress bar
        if progress_bar:
            progress_bar.start()
        
        aws_session = create_aws_session(input_access_key_id, input_secret_access_key, input_session_token)
        
        df_ris = get_ris(aws_session)
        df_ri_listings = get_ri_listings(aws_session)
        df_ri_utilization = get_ri_utilization(aws_session)

        # Only merge non-empty dataframes
        ri_df_list = [df for df in [df_ris, df_ri_utilization, df_ri_listings] if not df.empty]
        
        if ri_df_list:
            df_results = join_ri_util_listings(ri_df_list)
            # Also save to CSV
            df_results.to_csv("ris.csv", index=False)
        else:
            df_results = pd.DataFrame()
        
        # Stop progress bar
        if progress_bar:
            progress_bar.stop()
        if progress_var:
            progress_var.set("Data fetch completed!")
        
        print("Done!")
        
        # Show results window
        mainApp.after(100, show_results_window)
        
    except Exception as e:
        if progress_bar:
            progress_bar.stop()
        if progress_var:
            progress_var.set("Error occurred")
        messagebox.showerror("Error", f"An error occurred: {str(e)}")
        print(f"Error: {e}")

def get_aws_auth_parms():
    aws_access_key_id = aws_access_key_id_entry.get()
    aws_secret_access_key = aws_secret_access_key_entry.get()
    aws_session_token = aws_session_token_entry.get()

    if not all([aws_access_key_id, aws_secret_access_key, aws_session_token]):
        messagebox.showerror("Error", "Please fill in all AWS credential fields")
        return

    print("Running RI Inventory and Listings")
    
    # Run in separate thread to prevent UI freezing
    thread = threading.Thread(target=create_ri_inventory_and_listings, 
                            args=(aws_access_key_id, aws_secret_access_key, aws_session_token))
    thread.daemon = True
    thread.start()

# Create the AWS auth UI
mainApp = tk.Tk()
mainApp.title('AWS RI Inventory')
mainApp.geometry('520x550')
mainApp.configure(bg='white')

# Configure modern styling
style = ttk.Style()
style.theme_use('clam')

# Configure clean, modern styles
style.configure('Title.TLabel', font=('Arial', 16, 'bold'), background='white', foreground='#1a1a1a')
style.configure('Subtitle.TLabel', font=('Arial', 10), background='white', foreground='#666666')
style.configure('Field.TLabel', font=('Arial', 9), background='white', foreground='#333333')
style.configure('Modern.TEntry', fieldbackground='white', borderwidth=1, relief='solid', padding=8)
style.configure('Primary.TButton', font=('Arial', 10, 'bold'), padding=(20, 20))
style.configure('Secondary.TButton', font=('Arial', 10), padding=(15, 20))
style.configure('Modern.Horizontal.TProgressbar', 
               background='#007acc', 
               troughcolor='#e0e0e0',
               borderwidth=0,
               lightcolor='#007acc',
               darkcolor='#007acc')

# Main container
main_frame = ttk.Frame(mainApp, padding="30 25 30 25")
main_frame.pack(fill='both', expand=True)
main_frame.configure(style='White.TFrame')

# Configure white frame style
style.configure('White.TFrame', background='white')

# Title
title_label = ttk.Label(
    main_frame, 
    text='AWS Reserved Instance Inventory',
    style='Title.TLabel',
    background='white'
)
title_label.pack(pady=(0, 5))

subtitle_label = ttk.Label(
    main_frame, 
    text='Enter your AWS credentials to fetch and analyze RI data',
    style='Subtitle.TLabel',
    background='white'
)
subtitle_label.pack(pady=(0, 25))

# Credentials form
form_frame = ttk.Frame(main_frame)
form_frame.pack(fill='x', pady=(0, 20))
form_frame.configure(style='White.TFrame')

# ACCESS KEY ID
ttk.Label(form_frame, text='Access Key ID', style='Field.TLabel', background='white').pack(anchor='w', pady=(0, 3))
aws_access_key_id_entry = ttk.Entry(form_frame, style='Modern.TEntry', show='*')
aws_access_key_id_entry.pack(fill='x', pady=(0, 12))

# SECRET ACCESS KEY  
ttk.Label(form_frame, text='Secret Access Key', style='Field.TLabel', background='white').pack(anchor='w', pady=(0, 3))
aws_secret_access_key_entry = ttk.Entry(form_frame, style='Modern.TEntry', show='*')
aws_secret_access_key_entry.pack(fill='x', pady=(0, 12))

# SESSION TOKEN
ttk.Label(form_frame, text='Session Token', style='Field.TLabel', background='white').pack(anchor='w', pady=(0, 3))
aws_session_token_entry = ttk.Entry(form_frame, style='Modern.TEntry', show='*')
aws_session_token_entry.pack(fill='x')

# Status
status_frame = ttk.Frame(main_frame)
status_frame.pack(fill='x', pady=(20, 0))
status_frame.configure(style='White.TFrame')

progress_var = tk.StringVar(value="Ready to fetch data")
progress_label = ttk.Label(status_frame, textvariable=progress_var, style='Subtitle.TLabel', background='white')
progress_label.pack(pady=(0, 8))

progress_bar = ttk.Progressbar(status_frame, mode='indeterminate', style='Modern.Horizontal.TProgressbar')
progress_bar.pack(fill='x')

# Buttons
button_frame = ttk.Frame(main_frame)
button_frame.pack(pady=(25, 10))
button_frame.configure(style='White.TFrame')

button_OK = ttk.Button(
    button_frame, 
    text="Fetch Data", 
    command=get_aws_auth_parms,
    style='Primary.TButton',
    width=12
)
button_OK.pack(side='left', padx=(0, 10))

button_Cancel = ttk.Button(
    button_frame, 
    text="Cancel", 
    command=mainApp.quit,
    style='Secondary.TButton',
    width=10
)
button_Cancel.pack(side='left')

print("Starting application...")
mainApp.mainloop()