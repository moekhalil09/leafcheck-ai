# models/database.py - UPDATED VERSION
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, DuplicateKeyError
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any
from bson import ObjectId
import logging
from config import MONGODB_URI, DATABASE_NAME, SCANS_COLLECTION, PLANTS_COLLECTION, CLASS_NAMES
from models.data_models import ScanRecord, DiagnosisResult

logger = logging.getLogger(__name__)

class DatabaseManager:
    """MongoDB manager for LeafCheckAI with support for new model"""
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if not self._initialized:
            self.client = None
            self.db = None
            self._initialized = True
            self.connect()
    
    def connect(self):
        """Establish database connection"""
        try:
            self.client = MongoClient(MONGODB_URI, serverSelectionTimeoutMS=5000)
            # Test connection
            self.client.server_info()
            
            self.db = self.client[DATABASE_NAME]
            self.scans = self.db[SCANS_COLLECTION]
            self.plants = self.db[PLANTS_COLLECTION]
            
            # Create indexes
            self._create_indexes()
            
            logger.info(f"Connected to MongoDB: {DATABASE_NAME}")
            return True
            
        except ConnectionFailure as e:
            logger.error(f"MongoDB connection failed: {e}")
            return False
    
    def _create_indexes(self):
        """Create database indexes for better performance"""
        try:
            # Index for scanning by timestamp (descending)
            self.scans.create_index([("diagnosis.timestamp", -1)])
            
            # Index for scanning by disease name
            self.scans.create_index([("diagnosis.disease_name", 1)])
            
            # Index for scanning by is_rejected status
            self.scans.create_index([("diagnosis.is_rejected", 1)])
            
            # Index for scanning by confidence score
            self.scans.create_index([("diagnosis.confidence", -1)])
            
            # Index for plants by name
            self.plants.create_index([("name", 1)], unique=True)
            
            # Index for scanning by plant type
            self.scans.create_index([("plant_type", 1)])
            
            # Text index for searching in user notes
            self.scans.create_index([("user_notes", "text")])
            
            logger.info("Database indexes created successfully")
            
        except Exception as e:
            logger.error(f"Error creating indexes: {e}")
    
    def save_scan_record(self, scan_record: ScanRecord) -> Optional[str]:
        """Save a ScanRecord object to database"""
        try:
            # Convert ScanRecord to dictionary
            scan_dict = scan_record.to_dict()
            
            # Insert the scan
            result = self.scans.insert_one(scan_dict)
            
            scan_id = str(result.inserted_id)
            logger.info(f"Scan saved with ID: {scan_id} | "
                       f"Disease: {scan_record.diagnosis.disease.display_name if scan_record.diagnosis else 'None'} | "
                       f"Rejected: {scan_record.diagnosis.is_rejected if scan_record.diagnosis else False}")
            
            return scan_id
            
        except Exception as e:
            logger.error(f"Error saving scan record: {e}")
            return None
    
    def save_diagnosis(self, diagnosis: DiagnosisResult, 
                      plant_type: str = "tomato",
                      user_notes: str = "",
                      location: Optional[str] = None,
                      image_path: Optional[str] = None) -> Optional[str]:
        """Save a diagnosis with additional metadata"""
        try:
            scan_record = ScanRecord(
                plant_type=plant_type,
                image_path=image_path or diagnosis.image_path or "",
                diagnosis=diagnosis,
                user_notes=user_notes,
                location=location
            )
            
            return self.save_scan_record(scan_record)
            
        except Exception as e:
            logger.error(f"Error saving diagnosis: {e}")
            return None
    
    def get_recent_scans(self, limit: int = 20, include_rejected: bool = False) -> List[Dict]:
        """Get recent scan history"""
        try:
            query = {}
            if not include_rejected:
                query = {"diagnosis.is_rejected": False}
            
            scans = list(self.scans.find(query)
                         .sort("diagnosis.timestamp", -1)
                         .limit(limit))
            
            # Convert and enrich the data
            enriched_scans = []
            for scan in scans:
                scan["_id"] = str(scan["_id"])
                
                # Add formatted confidence percentage
                if "diagnosis" in scan:
                    confidence = scan["diagnosis"].get("confidence", 0)
                    scan["diagnosis"]["confidence_percent"] = f"{confidence:.1%}"
                    
                    # Add status indicator
                    if scan["diagnosis"].get("is_rejected", False):
                        scan["diagnosis"]["status"] = "Rejected"
                        scan["diagnosis"]["status_color"] = "gray"
                    elif scan["diagnosis"].get("disease_name") == "Tomato_Healthy":
                        scan["diagnosis"]["status"] = "Healthy"
                        scan["diagnosis"]["status_color"] = "green"
                    else:
                        scan["diagnosis"]["status"] = "Disease"
                        scan["diagnosis"]["status_color"] = "red"
                
                enriched_scans.append(scan)
            
            return enriched_scans
            
        except Exception as e:
            logger.error(f"Error getting recent scans: {e}")
            return []
    
    def get_scans_by_disease(self, disease_name: str, limit: int = 50) -> List[Dict]:
        """Get scans filtered by disease name"""
        try:
            scans = list(self.scans.find({"diagnosis.disease_name": disease_name})
                         .sort("diagnosis.timestamp", -1)
                         .limit(limit))
            
            for scan in scans:
                scan["_id"] = str(scan["_id"])
            
            return scans
            
        except Exception as e:
            logger.error(f"Error getting scans by disease: {e}")
            return []
    
    def get_scan_statistics(self, days: int = 30) -> Dict:
        """Get overall scan statistics with time filtering"""
        try:
            # Calculate date range
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days)
            
            # Total scans (all time)
            total_scans = self.scans.count_documents({})
            
            # Recent scans (within time range)
            recent_scans = self.scans.count_documents({
                "created_at": {"$gte": start_date}
            })
            
            # Accepted vs Rejected stats
            accepted_scans = self.scans.count_documents({
                "diagnosis.is_rejected": False
            })
            
            rejected_scans = self.scans.count_documents({
                "diagnosis.is_rejected": True
            })
            
            # Scans by disease (only accepted ones)
            pipeline = [
                {"$match": {"diagnosis.is_rejected": False}},
                {"$group": {
                    "_id": "$diagnosis.disease_name",
                    "count": {"$sum": 1},
                    "avg_confidence": {"$avg": "$diagnosis.confidence"}
                }},
                {"$sort": {"count": -1}}
            ]
            
            disease_stats = list(self.scans.aggregate(pipeline))
            
            # Daily scan count for the last 7 days
            daily_pipeline = [
                {"$match": {"created_at": {"$gte": end_date - timedelta(days=7)}}},
                {"$group": {
                    "_id": {"$dateToString": {"format": "%Y-%m-%d", "date": "$created_at"}},
                    "count": {"$sum": 1}
                }},
                {"$sort": {"_id": 1}}
            ]
            
            daily_stats = list(self.scans.aggregate(daily_pipeline))
            
            # Get top 3 most confident diagnoses
            top_confidence = list(self.scans.find({
                "diagnosis.is_rejected": False,
                "diagnosis.confidence": {"$gt": 0.8}
            })
            .sort("diagnosis.confidence", -1)
            .limit(3))
            
            for scan in top_confidence:
                scan["_id"] = str(scan["_id"])
            
            return {
                "total_scans": total_scans,
                "recent_scans": recent_scans,
                "accepted_scans": accepted_scans,
                "rejected_scans": rejected_scans,
                "rejection_rate": rejected_scans / total_scans if total_scans > 0 else 0,
                "disease_stats": disease_stats,
                "daily_stats": daily_stats,
                "top_confident": top_confidence,
                "time_range": {
                    "start": start_date.isoformat(),
                    "end": end_date.isoformat(),
                    "days": days
                }
            }
            
        except Exception as e:
            logger.error(f"Error getting statistics: {e}")
            return {}
    
    def get_disease_distribution(self) -> Dict:
        """Get distribution of all 8 diseases including rejected"""
        try:
            # Initialize with all diseases at 0
            distribution = {disease: 0 for disease in CLASS_NAMES}
            distribution["rejected"] = 0
            distribution["total"] = 0
            
            # Count by disease
            pipeline = [
                {"$group": {
                    "_id": "$diagnosis.disease_name",
                    "count": {"$sum": 1}
                }}
            ]
            
            results = list(self.scans.aggregate(pipeline))
            
            for result in results:
                disease_name = result["_id"]
                count = result["count"]
                distribution[disease_name] = count
                distribution["total"] += count
            
            return distribution
            
        except Exception as e:
            logger.error(f"Error getting disease distribution: {e}")
            return {}
    
    def get_scans_by_confidence_range(self, min_confidence: float = 0.0, 
                                     max_confidence: float = 1.0,
                                     limit: int = 50) -> List[Dict]:
        """Get scans filtered by confidence score range"""
        try:
            scans = list(self.scans.find({
                "diagnosis.confidence": {
                    "$gte": min_confidence,
                    "$lte": max_confidence
                }
            })
            .sort("diagnosis.confidence", -1)
            .limit(limit))
            
            for scan in scans:
                scan["_id"] = str(scan["_id"])
            
            return scans
            
        except Exception as e:
            logger.error(f"Error getting scans by confidence: {e}")
            return []
    
    def get_rejected_scans(self, limit: int = 50) -> List[Dict]:
        """Get scans that were rejected due to low confidence"""
        try:
            scans = list(self.scans.find({"diagnosis.is_rejected": True})
                         .sort("diagnosis.timestamp", -1)
                         .limit(limit))
            
            for scan in scans:
                scan["_id"] = str(scan["_id"])
            
            return scans
            
        except Exception as e:
            logger.error(f"Error getting rejected scans: {e}")
            return []
    
    def add_plant(self, plant_data: Dict) -> Optional[str]:
        """Add a plant to the database"""
        try:
            # Ensure required fields
            if "name" not in plant_data:
                raise ValueError("Plant name is required")
            
            # Add timestamps
            plant_data["created_at"] = datetime.now()
            plant_data["updated_at"] = datetime.now()
            
            result = self.plants.insert_one(plant_data)
            plant_id = str(result.inserted_id)
            
            logger.info(f"Plant added: {plant_data['name']} (ID: {plant_id})")
            return plant_id
            
        except DuplicateKeyError:
            logger.warning(f"Plant '{plant_data.get('name')}' already exists")
            return None
        except Exception as e:
            logger.error(f"Error adding plant: {e}")
            return None
    
    def get_all_plants(self) -> List[Dict]:
        """Get all plants"""
        try:
            plants = list(self.plants.find().sort("created_at", -1))
            
            for plant in plants:
                plant["_id"] = str(plant["_id"])
            
            return plants
            
        except Exception as e:
            logger.error(f"Error getting plants: {e}")
            return []
    
    def get_scan_by_id(self, scan_id: str) -> Optional[Dict]:
        """Get a specific scan by ID"""
        try:
            scan = self.scans.find_one({"_id": ObjectId(scan_id)})
            if scan:
                scan["_id"] = str(scan["_id"])
            return scan
            
        except Exception as e:
            logger.error(f"Error getting scan by ID: {e}")
            return None
    
    def delete_scan(self, scan_id: str) -> bool:
        """Delete a scan by ID"""
        try:
            result = self.scans.delete_one({"_id": ObjectId(scan_id)})
            success = result.deleted_count > 0
            
            if success:
                logger.info(f"Scan deleted: {scan_id}")
            else:
                logger.warning(f"Scan not found for deletion: {scan_id}")
            
            return success
            
        except Exception as e:
            logger.error(f"Error deleting scan: {e}")
            return False
    
    def cleanup_old_scans(self, days_old: int = 90) -> int:
        """Delete scans older than specified days"""
        try:
            cutoff_date = datetime.now() - timedelta(days=days_old)
            
            result = self.scans.delete_many({
                "created_at": {"$lt": cutoff_date}
            })
            
            deleted_count = result.deleted_count
            if deleted_count > 0:
                logger.info(f"Cleaned up {deleted_count} scans older than {days_old} days")
            
            return deleted_count
            
        except Exception as e:
            logger.error(f"Error cleaning up old scans: {e}")
            return 0
    
    def close(self):
        """Close database connection"""
        if self.client:
            self.client.close()
            logger.info("MongoDB connection closed")

# Singleton instance
db_manager = DatabaseManager()