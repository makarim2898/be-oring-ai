# from flask import Blueprint, Response, request, jsonify
# from flask_cors import CORS
# import pandas as pd

# information = Blueprint('information_routes', __name__)
# CORS(information)


# @information.route('/info/get-history', methods=['GET'])
# def info_history():
#     data = pd.read_csv('judgement.csv')
#     df = pd.DataFrame(data)

#     # Convert DataFrame to list of dictionaries
#     result = df.to_dict(orient='records')

#     # Return JSON response
#     return jsonify(result)

    
# @information.route('/info/tipu', methods=['GET'])
# def tipu_index():
#     return "info tipu-tipu-index"

from flask import Blueprint, request, jsonify
from flask_cors import CORS
import pandas as pd

information = Blueprint('information_routes', __name__)
CORS(information)

@information.route('/info/get-history', methods=['GET'])
def info_history():
    # Membaca data dari CSV
    data = pd.read_csv('judgement.csv')
    df = pd.DataFrame(data)

    # Mengambil semua parameter query dari request
    params = {
        'date': request.args.get('date'),
        'time': request.args.get('time'),
        'result': request.args.get('result'),
        'id': request.args.get('id'),
        'sort_by': request.args.get('sort_by', 'date'),  # Kolom untuk sort
        'sort_order': request.args.get('sort_order', 'asc'),  # Urutan sort: 'asc' atau 'desc'
        'group_by': request.args.get('group_by')  # Kolom untuk grouping
    }

    # Mengaplikasikan filter
    if params['date']:
        df = df[df['inspection_date'] == float(params['date'])]
    if params['time']:
        df = df[df['inspection_time'].astype(str).str.startswith(params['time'])]
    if params['result']:
        df = df[df['inspection_result'] == params['result']]
    if params['id']:
        df = df[df['inspection_id'] == int(params['id'])]

    # Menentukan arah pengurutan
    ascending = True if params['sort_order'] == 'asc' else False

    # Mengurutkan data berdasarkan kolom yang ditentukan
    sort_columns = []
    if params['sort_by'] == 'date':
        sort_columns.append('inspection_date')
    elif params['sort_by'] == 'time':
        sort_columns.append('inspection_time')
    elif params['sort_by'] == 'result':
        sort_columns.append('inspection_result')
    elif params['sort_by'] == 'id':
        sort_columns.append('inspection_id')

    if sort_columns:
        df = df.sort_values(by=sort_columns, ascending=ascending)

    # Grouping data jika parameter 'group_by' ada
    if params['group_by']:
        group_column = params['group_by']
        if group_column in df.columns:
            grouped_df = df.groupby(group_column).apply(lambda x: x.sort_values(by=sort_columns, ascending=ascending))
            grouped_df = grouped_df.reset_index(drop=True)
        else:
            return jsonify({"error": "Invalid group_by column"})
    else:
        grouped_df = df

    # Mengonversi DataFrame ke list of dictionaries
    result = grouped_df.to_dict(orient='records')

    # Mengembalikan response JSON
    return jsonify(result)

@information.route('/info/tipu', methods=['GET'])
def tipu_index():
    return "info tipu-tipu-index"
