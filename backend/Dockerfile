# LogiSight API — AWS Lambda Container Image
FROM public.ecr.aws/lambda/python:3.11

# Copy requirements and install
COPY requirements.txt ${LAMBDA_TASK_ROOT}/
RUN pip install --no-cache-dir -r ${LAMBDA_TASK_ROOT}/requirements.txt

# Copy application code
COPY app/ ${LAMBDA_TASK_ROOT}/app/
COPY alembic/ ${LAMBDA_TASK_ROOT}/alembic/
COPY alembic.ini ${LAMBDA_TASK_ROOT}/
COPY lambda_handler.py ${LAMBDA_TASK_ROOT}/

# Set the handler
CMD ["lambda_handler.handler"]
