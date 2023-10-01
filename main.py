from functions import *
from limiter import RateLimiter

app = Flask(__name__)

redis_host = 'localhost'
redis_port = 6379
max_requests = 50
time_window = 60  # 60 seconds

limiter = RateLimiter(redis_host, redis_port, time_window)

@app.errorhandler(404)
def page_not_found(e):
    return error_response(404, 'Page Not Found')

@app.errorhandler(500)
def internal_server_error(e):
    return error_response(500, 'Internal Server Error')

@app.errorhandler(ValueError)
def handle_value_error(e):
    return error_response(400, 'Bad Request: Invalid Value')

@app.errorhandler(429)
def ratelimit_handler(e):
  return error_response(429, '"You have exceeded your rate-limit"')

@app.route('/download/<string:file_name>')
def download_file(file_name):
    try:
        file_type = get_file_type(file_name)  # Implement this function to extract file type from file_name
        limit = determine_rate_limit(file_type)
    except Exception as e:
        print(e)
        limit = 5 # Default rate limit if file type is unknown or an error occurs

    identifier = get_remote_address()  # Identify by IP address
    if limiter.is_request_allowed(identifier, limit):
        return "Too many requests. Please try again later.", 429  # HTTP status code 429 indicates Too Many Requests
    else:
        THIS_FOLDER = Path(__file__).parent.resolve()
        file_path = THIS_FOLDER / f"files/{file_name}"
        return send_file(file_path, as_attachment=True)

@app.route('/', methods=['GET', 'POST'])
def upload():

    THIS_FOLDER = Path(__file__).parent.resolve()
    directory = THIS_FOLDER / f"files"

    if request.method == 'GET':

        pipeline = [
            {
                "$group": {
                    "_id": "$smart_category",
                    "files": {
                        "$push": {
                            "name": "$name",
                            "category": "$category",
                            "smart_category": "$smart_category"
                        }
                    }
                }
            }
        ]

        # group by smart category
        uploaded_files = list(collection.aggregate(pipeline))
        return render_template('portal.html', uploaded_files=uploaded_files)

    elif request.method == 'POST':

        # get existing categories to make easier to group
        field_name = 'smart_category'
        unique_field_values = [field for field in collection.distinct(field_name) if field]
        past_categories = ", ".join(unique_field_values) if unique_field_values else "Resume, Finance, Article, Advice"

        # if files directory doesn't exist, create it
        if not os.path.exists(directory):
            os.makedirs(directory, exist_ok=True) 

        if "content[]" in request.files:
            content_docs = request.files.getlist('content[]') # files to be uploaded
            to_delete = request.form['delete'] # files to be deleted
            
            # DELETE: get existing files and if it's in the to_delete list, delete the file
            # Sanitize file names to be secure
            file_list = [secure_filename(f) for f in os.listdir(directory) if os.path.isfile(os.path.join(directory, f))]
            if file_list and to_delete:
                for file_name in file_list.copy(): # Create a copy of file_list to iterate over since we're using a For loop
                    if file_name in to_delete:
                        collection.delete_many({"name": file_name}) 
                        os.remove(os.path.join(directory, file_name))
                        file_list.remove(file_name)

            start_time = time.perf_counter()

            # UPLOAD: Using ProcessPoolExecutor for concurrent execution of smart_categorize function
            try: 
                with concurrent.futures.ProcessPoolExecutor() as executor:
                    for file_item in content_docs:
                        
                        sanitized_filename = secure_filename(file_item.filename)

                        # if existing file, remove and replace
                        existing_file = collection.find_one({"name": sanitized_filename})
                        if existing_file:
                            existing_file_path = os.path.join(directory, sanitized_filename)
                            if os.path.exists(existing_file_path):
                                os.remove(existing_file_path)
                            collection.delete_many({"name": sanitized_filename}) 

                        # check if exists and upload
                        if sanitized_filename: 
                            new_file_path = os.path.join(directory, sanitized_filename)
                            file_item.save(new_file_path) 
                            file_type = get_file_type(new_file_path)

                            # Submit the task to the executor
                            future = executor.submit(smart_categorize, new_file_path, file_type, past_categories)

                            # insert file into database
                            file_name = os.path.basename(new_file_path)

                            smart_category = future.result()
                            
                            new_doc = {
                                "name": file_name,
                                "category": file_type,
                                "smart_category": smart_category,
                            }

                            collection.insert_one(new_doc)

                            # update past categories list to improve model
                            if smart_category not in past_categories:
                                past_categories += ", " + smart_category
                
                # group by smart category
                pipeline = [
                    {
                        "$group": {
                            "_id": "$smart_category",
                            "files": {
                                "$push": {
                                    "name": "$name",
                                    "category": "$category",
                                    "smart_category": "$smart_category"
                                }
                            }
                        }
                    }
                ]

                uploaded_files = list(collection.aggregate(pipeline))

                # time it took
                end_time = time.perf_counter()
                elapsed_time = end_time - start_time
                print("Elapsed time:", elapsed_time, "seconds")
                return render_template('portal.html', uploaded_files=uploaded_files)
            
            except Exception as e:
                
                print(e)

                raise ValueError("There's an Issue with One of Your Files")

    else:

        raise ValueError('Request Not Allowed')

if __name__ == '__main__':
    app.run(debug=True)
