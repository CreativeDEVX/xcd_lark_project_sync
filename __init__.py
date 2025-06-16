import logging
from . import models
from . import wizards
from . import uninstall_hook
from .post_init_hook import post_init_hook

_logger = logging.getLogger(__name__)

def pre_init_hook(cr):
    """Pre-init hook to prepare the module installation"""
    _logger.info("Running pre-init hook for Lark Project Sync")

def post_load():
    """Post-load hook to execute after module is loaded"""
    _logger.info("Lark Project Sync module loaded")

# Execute post-load hook when module is loaded
post_load()

__all__ = ['post_init_hook', 'uninstall_hook', 'pre_init_hook']