"""
Background job history model.

Tracks execution of background jobs for monitoring and debugging.
"""

from datetime import datetime
from .base import db, TimestampMixin


class JobHistory(db.Model, TimestampMixin):
    """
    History of background job executions.
    
    Tracks job status, progress, and errors for monitoring and debugging.
    Supports Issue #137 (Scheduled Jobs and Status Tracking).
    """
    __tablename__ = 'job_history'
    
    id = db.Column(db.Integer, primary_key=True)
    
    # Job identification
    job_id = db.Column(db.String(100), nullable=False, unique=True, index=True)
    job_type = db.Column(db.String(50), nullable=False, index=True)  # 'analysis', 'sync', 'geocoding', etc.
    job_name = db.Column(db.String(200), nullable=False)
    
    # Job status
    status = db.Column(db.String(20), nullable=False, index=True)  # 'queued', 'running', 'completed', 'failed', 'cancelled'
    progress = db.Column(db.Float, nullable=False, default=0.0)  # 0.0 to 1.0
    
    # Timing
    queued_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    started_at = db.Column(db.DateTime, nullable=True)
    completed_at = db.Column(db.DateTime, nullable=True)
    duration_seconds = db.Column(db.Float, nullable=True)
    
    # Results
    result_summary = db.Column(db.Text, nullable=True)  # JSON-encoded summary
    error_message = db.Column(db.Text, nullable=True)
    error_traceback = db.Column(db.Text, nullable=True)
    
    # Metadata
    parameters = db.Column(db.Text, nullable=True)  # JSON-encoded job parameters
    triggered_by = db.Column(db.String(50), nullable=True)  # 'user', 'schedule', 'system'
    
    def __repr__(self):
        return f'<JobHistory {self.job_id} {self.job_type} {self.status}>'
    
    def to_dict(self):
        """Convert to dictionary for API responses."""
        import json
        return {
            'id': self.id,
            'job_id': self.job_id,
            'job_type': self.job_type,
            'job_name': self.job_name,
            'status': self.status,
            'progress': self.progress,
            'queued_at': self.queued_at.isoformat() if self.queued_at else None,
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'duration_seconds': self.duration_seconds,
            'result_summary': json.loads(self.result_summary) if self.result_summary else None,
            'error_message': self.error_message,
            'parameters': json.loads(self.parameters) if self.parameters else None,
            'triggered_by': self.triggered_by,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
    
    def start(self):
        """Mark job as started."""
        self.status = 'running'
        self.started_at = datetime.utcnow()
        db.session.commit()
    
    def update_progress(self, progress, message=None):
        """
        Update job progress.
        
        Args:
            progress: Progress value (0.0 to 1.0)
            message: Optional progress message
        """
        self.progress = max(0.0, min(1.0, progress))
        if message:
            import json
            summary = json.loads(self.result_summary) if self.result_summary else {}
            summary['progress_message'] = message
            self.result_summary = json.dumps(summary)
        db.session.commit()
    
    def complete(self, result_summary=None):
        """
        Mark job as completed.
        
        Args:
            result_summary: Optional result summary (dict)
        """
        import json
        self.status = 'completed'
        self.progress = 1.0
        self.completed_at = datetime.utcnow()
        if self.started_at:
            self.duration_seconds = (self.completed_at - self.started_at).total_seconds()
        if result_summary:
            self.result_summary = json.dumps(result_summary)
        db.session.commit()
    
    def fail(self, error_message, error_traceback=None):
        """
        Mark job as failed.
        
        Args:
            error_message: Error message
            error_traceback: Optional full traceback
        """
        self.status = 'failed'
        self.completed_at = datetime.utcnow()
        if self.started_at:
            self.duration_seconds = (self.completed_at - self.started_at).total_seconds()
        self.error_message = error_message
        self.error_traceback = error_traceback
        db.session.commit()
    
    def cancel(self):
        """Mark job as cancelled."""
        self.status = 'cancelled'
        self.completed_at = datetime.utcnow()
        if self.started_at:
            self.duration_seconds = (self.completed_at - self.started_at).total_seconds()
        db.session.commit()
    
    @classmethod
    def create_job(cls, job_type, job_name, parameters=None, triggered_by='user'):
        """
        Create a new job record.
        
        Args:
            job_type: Type of job
            job_name: Human-readable job name
            parameters: Optional job parameters (dict)
            triggered_by: Who/what triggered the job
            
        Returns:
            JobHistory instance
        """
        import json
        from datetime import datetime
        
        job_id = f"{job_type}-{datetime.utcnow().strftime('%Y%m%d-%H%M%S')}"
        
        job = cls(
            job_id=job_id,
            job_type=job_type,
            job_name=job_name,
            status='queued',
            parameters=json.dumps(parameters) if parameters else None,
            triggered_by=triggered_by
        )
        
        db.session.add(job)
        db.session.commit()
        
        return job
    
    @classmethod
    def get_recent(cls, limit=50, job_type=None, status=None):
        """
        Get recent jobs.
        
        Args:
            limit: Maximum number of jobs to return
            job_type: Optional filter by job type
            status: Optional filter by status
            
        Returns:
            List of JobHistory instances
        """
        query = cls.query
        
        if job_type:
            query = query.filter_by(job_type=job_type)
        if status:
            query = query.filter_by(status=status)
        
        return query.order_by(cls.created_at.desc()).limit(limit).all()
    
    @classmethod
    def cleanup_old(cls, days=30):
        """
        Delete job records older than specified days.
        
        Args:
            days: Number of days to keep
            
        Returns:
            Number of records deleted
        """
        from datetime import timedelta
        cutoff = datetime.utcnow() - timedelta(days=days)
        
        old_jobs = cls.query.filter(cls.created_at < cutoff).all()
        count = len(old_jobs)
        
        for job in old_jobs:
            db.session.delete(job)
        
        db.session.commit()
        return count

# Made with Bob
