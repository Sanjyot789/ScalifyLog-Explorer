import logging
import psycopg2
from flask import Flask, render_template, request, jsonify

app = Flask(__name__)

# Logger setup
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# PostgresSQL connection setup
conn = psycopg2.connect(
    dbname='dyte_logs',
    user='postgres',
    password='1234',
    host='localhost',
    port='5432'
)
cursor = conn.cursor()

# Create logs table if not exists
cursor.execute('''
    CREATE TABLE IF NOT EXISTS logs (
        id SERIAL PRIMARY KEY,
        level TEXT,
        message TEXT,
        resourceId TEXT,
        timestamp TIMESTAMP,
        traceId TEXT,
        spanId TEXT,
        commit TEXT,
        parentResourceId TEXT
    )
''')
conn.commit()


# Function to fetch logs from PostgreSQL
def fetch_logs_from_postgres():
    query = 'SELECT * FROM logs'
    cursor.execute(query)
    columns = [desc[0] for desc in cursor.description]
    logs = cursor.fetchall()
    return {'columns': columns, 'data': logs}


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/ingest', methods=['POST'])
def ingest_log():
    log_data = request.get_json()
    ingest_log_into_postgres(log_data)
    return "Log ingested successfully"


@app.route('/search', methods=['GET'])
def search_logs():
    level = request.args.get('level')
    message = request.args.get('message')
    resourceId = request.args.get('resourceId')
    timestamp = request.args.get('timestamp')
    traceId = request.args.get('traceId')
    spanId = request.args.get('spanId')
    commit = request.args.get('commit')
    parentResourceId = request.args.get('parentResourceId')
    startdate = request.args.get('startdate')
    enddate = request.args.get('enddate')

    app.logger.info(
        f"Received search request. Level: {level}, Message: {message}, Resource ID: {resourceId}, Timestamp: {timestamp}, Trace ID: {traceId}, Span ID: {spanId}, Commit: {commit}, Parent Resource ID: {parentResourceId}")

    filters = {
        'level': level,
        'message': message,
        'resourceId': resourceId,
        'timestamp': timestamp,
        'traceId': traceId,
        'spanId': spanId,
        'commit': commit,
        'parentresourceid': parentResourceId,  # Corrected field name
        'startdate': startdate,
        'enddate': enddate
    }

    app.logger.info(f"Applying filters: {filters}")

    logs = search_logs_in_postgres(filters)
    app.logger.info(f"Search results: {logs}")
    # print(jsonify(logs))
    return jsonify(logs)


def search_logs_in_postgres(filters):
    query = 'SELECT * FROM logs WHERE '
    conditions = []

    for key, value in filters.items():
        if value:
            if key == 'startdate' or key == 'enddate':
                conditions.append(f"timestamp::date {'>=' if key == 'startdate' else '<='} '{value}'")
            else:
                conditions.append(f"{key} = '{value}'")
            # If the value is not empty, add it to the conditions
            # conditions.append(f"{key} = '{value}'")

    # Check if there are any conditions before adding them to the query
    if conditions:
        query += ' AND '.join(conditions)
        cursor.execute(query)
        columns = [desc[0] for desc in cursor.description]
        logs = cursor.fetchall()
        return {'columns': columns, 'data': logs}
    else:
        # If no conditions are specified, return all logs
        return fetch_logs_from_postgres()


def ingest_log_into_postgres(log_data):
    query = '''
        INSERT INTO logs (level, message, resourceId, timestamp, traceId, spanId, commit, parentResourceId)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
    '''
    cursor.execute(query, (
        log_data['level'],
        log_data['message'],
        log_data['resourceId'],
        log_data['timestamp'],
        log_data['traceId'],
        log_data['spanId'],
        log_data['commit'],
        log_data['metadata']['parentResourceId'] if 'metadata' in log_data and 'parentResourceId' in log_data[
            'metadata'] else None
    ))
    conn.commit()


if __name__ == "__main__":
    app.run(port=3000, debug=True)
