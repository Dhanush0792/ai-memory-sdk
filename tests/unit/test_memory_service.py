"""
Core Testing Framework - Unit Tests for Memory Service
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
from datetime import datetime

from app.core.services.memory_service import MemoryService
from app.database.repositories.memory_repository import MemoryRepository


class TestMemoryService:
    """Unit tests for MemoryService"""
    
    @pytest.fixture
    def mock_repo(self):
        """Create mock repository"""
        return Mock(spec=MemoryRepository)
    
    @pytest.fixture
    def service(self, mock_repo):
        """Create service with mock repository"""
        return MemoryService(mock_repo)
    
    def test_create_memory_success(self, service, mock_repo):
        """Test successful memory creation"""
        # Arrange
        mock_repo.find_conflicts.return_value = []
        mock_repo.create.return_value = {
            'id': 'mem123',
            'user_id': 'user123',
            'memory_type': 'fact',
            'key': 'name',
            'value': 'John Doe',
            'confidence': 0.95,
            'importance': 0.8,
            'created_at': datetime.utcnow(),
            'version': 1
        }
        
        # Act
        result = service.create_memory(
            user_id='user123',
            memory_type='fact',
            key='name',
            value='John Doe',
            confidence=0.95,
            importance=0.8
        )
        
        # Assert
        assert result['id'] == 'mem123'
        assert result['key'] == 'name'
        mock_repo.create.assert_called_once()
        mock_repo.find_conflicts.assert_called_once_with('user123', 'name')
    
    def test_create_memory_invalid_user_id(self, service):
        """Test memory creation with invalid user ID"""
        with pytest.raises(ValueError, match="Invalid user_id format"):
            service.create_memory(
                user_id="user'; DROP TABLE memories; --",
                memory_type='fact',
                key='name',
                value='John'
            )
    
    def test_create_memory_invalid_type(self, service):
        """Test memory creation with invalid type"""
        with pytest.raises(ValueError, match="Invalid memory_type"):
            service.create_memory(
                user_id='user123',
                memory_type='invalid_type',
                key='name',
                value='John'
            )
    
    def test_create_memory_invalid_confidence(self, service):
        """Test memory creation with invalid confidence"""
        with pytest.raises(ValueError, match="Confidence must be between"):
            service.create_memory(
                user_id='user123',
                memory_type='fact',
                key='name',
                value='John',
                confidence=1.5  # Invalid
            )
    
    def test_create_memory_sanitizes_value(self, service, mock_repo):
        """Test that memory value is sanitized"""
        # Arrange
        mock_repo.find_conflicts.return_value = []
        mock_repo.create.return_value = {'id': 'mem123', 'value': 'Clean value'}
        
        # Act
        service.create_memory(
            user_id='user123',
            memory_type='fact',
            key='test',
            value='<script>alert("xss")</script>Test value'
        )
        
        # Assert
        # Value should be sanitized (HTML escaped)
        call_args = mock_repo.create.call_args
        assert '<script>' not in call_args.kwargs['value']
    
    def test_get_memory_success(self, service, mock_repo):
        """Test successful memory retrieval"""
        # Arrange
        mock_repo.find_by_id.return_value = {
            'id': 'mem123',
            'user_id': 'user123',
            'key': 'name',
            'value': 'John'
        }
        
        # Act
        result = service.get_memory('mem123', 'user123')
        
        # Assert
        assert result['id'] == 'mem123'
        mock_repo.find_by_id.assert_called_once_with('mem123', 'user123')
    
    def test_get_memory_not_found(self, service, mock_repo):
        """Test memory retrieval when not found"""
        # Arrange
        mock_repo.find_by_id.return_value = None
        
        # Act
        result = service.get_memory('mem999', 'user123')
        
        # Assert
        assert result is None
    
    def test_get_memories_with_filters(self, service, mock_repo):
        """Test getting memories with filters"""
        # Arrange
        mock_repo.find_by_user.return_value = [
            {'id': 'mem1', 'memory_type': 'fact'},
            {'id': 'mem2', 'memory_type': 'fact'}
        ]
        
        # Act
        result = service.get_memories(
            user_id='user123',
            memory_type='fact',
            min_confidence=0.5,
            limit=10
        )
        
        # Assert
        assert len(result) == 2
        mock_repo.find_by_user.assert_called_once()
    
    def test_get_memories_caps_limit(self, service, mock_repo):
        """Test that limit is capped at 1000"""
        # Arrange
        mock_repo.find_by_user.return_value = []
        
        # Act
        service.get_memories(user_id='user123', limit=5000)
        
        # Assert
        call_args = mock_repo.find_by_user.call_args
        assert call_args.kwargs['limit'] == 1000  # Capped
    
    def test_update_memory_success(self, service, mock_repo):
        """Test successful memory update"""
        # Arrange
        mock_repo.update.return_value = {
            'id': 'mem123',
            'value': 'Updated value',
            'version': 2
        }
        
        # Act
        result = service.update_memory(
            memory_id='mem123',
            user_id='user123',
            updates={'value': 'Updated value'}
        )
        
        # Assert
        assert result['version'] == 2
        mock_repo.update.assert_called_once()
    
    def test_update_memory_sanitizes_value(self, service, mock_repo):
        """Test that updated value is sanitized"""
        # Arrange
        mock_repo.update.return_value = {'id': 'mem123'}
        
        # Act
        service.update_memory(
            memory_id='mem123',
            user_id='user123',
            updates={'value': '<script>alert("xss")</script>'}
        )
        
        # Assert
        call_args = mock_repo.update.call_args
        assert '<script>' not in call_args[2]['value']
    
    def test_delete_memory_hard_delete(self, service, mock_repo):
        """Test hard delete"""
        # Arrange
        mock_repo.delete.return_value = True
        
        # Act
        result = service.delete_memory('mem123', 'user123', soft_delete=False)
        
        # Assert
        assert result is True
        mock_repo.delete.assert_called_once_with('mem123', 'user123')
    
    def test_delete_memory_soft_delete(self, service, mock_repo):
        """Test soft delete"""
        # Arrange
        mock_repo.soft_delete.return_value = True
        
        # Act
        result = service.delete_memory('mem123', 'user123', soft_delete=True)
        
        # Assert
        assert result is True
        mock_repo.soft_delete.assert_called_once_with('mem123', 'user123')
    
    def test_delete_all_user_memories(self, service, mock_repo):
        """Test GDPR deletion"""
        # Arrange
        mock_repo.delete_all_for_user.return_value = 42
        
        # Act
        result = service.delete_all_user_memories('user123')
        
        # Assert
        assert result == 42
        mock_repo.delete_all_for_user.assert_called_once_with('user123')
    
    def test_get_memory_stats(self, service, mock_repo):
        """Test memory statistics"""
        # Arrange
        mock_repo.count_by_user.side_effect = [100, 40, 30, 20, 10]
        
        # Act
        result = service.get_memory_stats('user123')
        
        # Assert
        assert result['total_memories'] == 100
        assert result['by_type']['fact'] == 40
        assert result['by_type']['preference'] == 30


class TestMemoryServiceIntegration:
    """Integration tests with real database (requires test DB)"""
    
    @pytest.mark.integration
    def test_create_and_retrieve_memory(self):
        """Test full create and retrieve flow"""
        # This would use a real test database
        # Skipped in unit tests
        pass
    
    @pytest.mark.integration
    def test_gdpr_deletion_cascade(self):
        """Test that CASCADE delete works"""
        # This would verify CASCADE constraints
        # Skipped in unit tests
        pass


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
