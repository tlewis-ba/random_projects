#!/usr/bin/env python3
"""
Tests for DevTool CLI
"""
import subprocess
import pytest
from unittest.mock import patch, MagicMock
from devtool.cli import (
    run_command, 
    get_docker_containers, 
    get_git_worktrees, 
    find_repos_in_workspace,
    cmd_list,
    cmd_status
)

class TestRunCommand:
    """Test the run_command function."""
    
    def test_successful_command(self):
        """Test successful command execution."""
        result = run_command(["echo", "hello"])
        assert result.returncode == 0
        assert "hello" in result.stdout
    
    def test_failed_command(self):
        """Test failed command execution."""
        result = run_command(["false"])
        assert result.returncode == 1

class TestDockerContainers:
    """Test Docker container discovery."""
    
    @patch('devtool.cli.run_command')
    def test_get_docker_containers_success(self, mock_run):
        """Test successful Docker container listing."""
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = '{"ID":"abc123","Names":"test-container","Image":"ubuntu","Status":"Up","Ports":"8080->80"}'
        mock_run.return_value = mock_result
        
        containers = get_docker_containers()
        assert len(containers) == 1
        assert containers[0]['name'] == 'test-container'
    
    @patch('devtool.cli.run_command')
    def test_get_docker_containers_no_containers(self, mock_run):
        """Test when no containers are running."""
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = ''
        mock_run.return_value = mock_result
        
        containers = get_docker_containers()
        assert len(containers) == 0

class TestGitWorktrees:
    """Test Git worktree discovery."""
    
    @patch('os.path.exists')
    @patch('devtool.cli.run_command')
    def test_get_git_worktrees_success(self, mock_run_command, mock_exists):
        """Test successful worktree listing."""
        mock_exists.return_value = True
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = '/path/to/repo 1234567890abcdef [main]\n/path/to/repo/sub 1234567890abcdef [feature-branch]'
        mock_run_command.return_value = mock_result
        
        worktrees = get_git_worktrees('/path/to/repo')
        assert len(worktrees) == 2
        assert worktrees[0]['branch'] == '1234567890abcdef'
        assert worktrees[1]['branch'] == '[feature-branch]'
    
    @patch('devtool.cli.run_command')
    def test_get_git_worktrees_no_repo(self, mock_run):
        """Test when repository doesn't exist."""
        with patch('os.path.exists', return_value=False):
            worktrees = get_git_worktrees('/nonexistent')
            assert len(worktrees) == 0

class TestRepoDiscovery:
    """Test repository discovery in workspace."""
    
    @patch('os.path.exists')
    @patch('os.walk')
    def test_find_repos_in_workspace(self, mock_walk, mock_exists):
        """Test finding repositories in workspace."""
        mock_exists.return_value = True
        mock_walk.return_value = [
            ('/home/user/dev', ['.git', 'subdir'], []),
            ('/home/user/dev/subdir', ['.git'], [])
        ]
        
        repos = find_repos_in_workspace('/home/user/dev')
        assert len(repos) == 2
        assert '/home/user/dev' in repos

class TestCLICommands:
    """Test CLI command functions."""
    
    @patch('builtins.print')
    @patch('devtool.cli.get_docker_containers')
    @patch('devtool.cli.find_repos_in_workspace')
    def test_cmd_list(self, mock_find_repos, mock_get_containers, mock_print):
        """Test the list command."""
        mock_get_containers.return_value = [{'name': 'test', 'image': 'ubuntu', 'status': 'Up'}]
        mock_find_repos.return_value = ['/path/to/repo']
        
        args = MagicMock()
        cmd_list(args)
        
        # Verify print was called (we don't need to check exact output)
        assert mock_print.called
    
    @patch('builtins.print')
    @patch('devtool.cli.run_command')
    @patch('os.path.exists')
    def test_cmd_status(self, mock_exists, mock_run, mock_print):
        """Test the status command."""
        # Mock successful commands
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_run.return_value = mock_result
        mock_exists.return_value = True
        
        args = MagicMock()
        cmd_status(args)
        
        # Verify print was called
        assert mock_print.called

if __name__ == "__main__":
    pytest.main([__file__])
