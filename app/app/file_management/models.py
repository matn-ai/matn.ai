from datetime import datetime
from sqlalchemy.dialects.mysql import LONGTEXT
from sqlalchemy import JSON
from sqlalchemy.dialects.postgresql import UUID
import uuid, time
from .. import db


import os
import boto3
from botocore.client import Config
from botocore.exceptions import ClientError, EndpointConnectionError
from flask import current_app
from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.sql import func


class File(db.Model):
    __tablename__ = 'files'

    id = Column(UUID(as_uuid=True), nullable=False, 
                default=uuid.uuid4,
                primary_key=True)
    bucket = Column(String(255), nullable=False)
    file_name = Column(String(255), nullable=False)
    content_type = Column(String(100))
    size = Column(Integer)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    @classmethod
    def upload_file(cls, local_file_path, bucket, file_name, content_type=None):
        # Initialize S3 client
        s3_client = boto3.client(
            's3',
            endpoint_url=current_app.config['S3_ENDPOINT_URL'],
            aws_access_key_id=current_app.config['S3_ACCESS_KEY'],
            aws_secret_access_key=current_app.config['S3_SECRET_KEY'],
            config=Config(signature_version='s3v4')
        )
        # Get file size and content type
        file_size = os.path.getsize(local_file_path)
        if not content_type:
            content_type = current_app.config['S3_DEFAULT_CONTENT_TYPE']
        s3_client.list_buckets()
        # Upload the file
        
        s3_client.upload_file(
            local_file_path, 
            bucket, 
            file_name,
            # Callback=lambda bytes_transferred: cls._upload_progress(bytes_transferred, file_size, start_time)
            # ExtraArgs={'ContentType': content_type}
        )
        # Create a new File record in the database
        new_file = cls(
            bucket=bucket,
            file_name=file_name,
            content_type=content_type,
            size=file_size
        )
        db.session.add(new_file)
        db.session.commit()

        return new_file
        
    def get_file_url(self):
        # Initialize S3 client
        s3_client = boto3.client(
            's3',
            endpoint_url=current_app.config['S3_ENDPOINT_URL'],
            aws_access_key_id=current_app.config['S3_ACCESS_KEY'],
            aws_secret_access_key=current_app.config['S3_SECRET_KEY'],
            config=boto3.session.Config(signature_version='s3v4')
        )

        # Generate a presigned URL for the file
        url = s3_client.generate_presigned_url(
            'get_object',
            Params={'Bucket': self.bucket, 'Key': self.file_name},
            ExpiresIn=current_app.config['S3_PRESIGNED_URL_EXPIRATION']
        )
        return url

    def create_public_url(self):
        try:
            # Initialize S3 client
            s3_client = boto3.client(
                's3',
                endpoint_url=current_app.config['S3_ENDPOINT_URL'],
                aws_access_key_id=current_app.config['S3_ACCESS_KEY'],
                aws_secret_access_key=current_app.config['S3_SECRET_KEY'],
                config=boto3.session.Config(signature_version='s3v4')
            )

            # Set the object to be publicly readable
            s3_client.put_object_acl(
                ACL='public-read',
                Bucket=self.bucket,
                Key=self.file_name
            )

            # Construct the public URL
            if current_app.config['S3_ENDPOINT_URL']:
                # For custom S3-compatible storage like MinIO
                public_url = f"{current_app.config['S3_ENDPOINT_URL']}/{self.bucket}/{self.file_name}"
            else:
                # For AWS S3
                region = s3_client.get_bucket_location(Bucket=self.bucket)['LocationConstraint']
                public_url = f"https://{self.bucket}.s3.{region}.amazonaws.com/{self.file_name}"

            return public_url

        except ClientError as e:
            current_app.logger.error(f"Error creating public URL: {str(e)}")
            return None

    @classmethod
    def get_file(cls, id):
        return cls.query.get(id)




class ContentFile(db.Model):
    __tablename__ = 'content_files'
    id = Column(UUID(as_uuid=True), nullable=False, 
                default=uuid.uuid4,
                primary_key=True)
    
    file = db.relationship('File', backref='content_file', uselist=False)
    content_id = db.Column(db.Integer, db.ForeignKey('contents.id'))
    file_id = Column(UUID(as_uuid=True), db.ForeignKey('files.id'))
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    @classmethod
    def add_file_for_content(cls, content_id, file_id):
        try:
            new_content_file = cls(
                content_id=content_id,
                file_id=file_id
            )
            db.session.add(new_content_file)
            db.session.commit()
            return new_content_file
        except Exception as e:
            current_app.logger.error(f"Error adding file for content: {str(e)}")
            return None

    @classmethod
    def get_files_for_content(cls, content_id):
        try:
            return cls.query.filter_by(content_id=content_id).all()
        except Exception as e:
            current_app.logger.error(f"Error getting files for content: {str(e)}")
            return None
