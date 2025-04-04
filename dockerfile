FROM python
WORKDIR /app

# Copy application code
COPY movie.py /app
COPY ChatGPT_HKBU.py /app
COPY config.ini /app
COPY requirements.txt /app

RUN pip install --upgrade pip
RUN pip install -r requirements.txt
RUN pip install update
RUN pip install standard-imghdr

# Command to run your application
CMD ["python", "movie.py"]