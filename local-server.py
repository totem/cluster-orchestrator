import os
from conf.appconfig import API_PORT, BOOLEAN_TRUE_VALUES
from orchestrator.server import app


if __name__ == '__main__':
    app.run(debug=os.getenv('FLASK_DEBUG', 'false').strip().lower() in
            BOOLEAN_TRUE_VALUES,
            threaded=True,
            host='0.0.0.0',
            port=API_PORT)
