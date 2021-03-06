# coding: utf-8
from __future__ import print_function
"""
(c) 2013 - Ronan Delacroix
Logging Utils
:author: Ronan Delacroix
"""
import sys
import os
import socket
import logging
import logging.handlers
from . import code


def configure_logging_to_screen(debug=False):
    level = 'INFO'
    if debug:
        level = 'DEBUG'
    (script_folder, app_name) = code.get_app_name()
    settings = {'LOGGING_SCREEN_LEVEL': level, 'LOGGING_METHODS': ['SCREEN'], 'LOGGING_SCREEN_FORMAT': '%(levelname)-8s| %(message)s'}
    configure_logger(logging.getLogger(), app_name, settings=settings)


def configure_logging(log_name, settings={}, application_name=None, force=False):
    configure_logger(logging.getLogger(), log_name, settings=settings, application_name=application_name, force=force)


def configure_logger(logger, log_name, settings={}, application_name=None, force=False):

    log_level = settings.get('LOGGING_LEVEL', 'DEBUG')
    log_methods = settings.get('LOGGING_METHODS', ['SCREEN', 'FILE'])

    logger.setLevel(log_level)
    
    if not hasattr(logger, 'handlers_added') or force:
        #we first remove all handlers  
        for handler in logger.handlers:
            logger.removeHandler(handler)

        #make handlers, that write the logs to screen, file, syslog
        if 'SCREEN' in log_methods:
            add_screen_logging(logger, settings)

        if 'SYSLOG' in log_methods:# and ('SysLogHandler' in dir(logging)):
            add_syslog_logging(logger, log_name, settings)

        if 'FILE' in log_methods:
            add_file_logging(logger, log_name, application_name, settings)

        if 'MONGO' in log_methods:
            add_mongo_logging(logger, log_name, application_name, settings)

        logger.propagate = True
    
        logger.handlers_added = True


def add_screen_logging(logger, settings={}):
    screen_format = settings.get('LOGGING_SCREEN_FORMAT', '%(levelname)-8s| %(message)s')
    level = settings.get('LOGGING_SCREEN_LEVEL', None)
    write_to_screen_handler = logging.StreamHandler()
    screen_formatter = logging.Formatter(screen_format, '%Y-%m-%dT%H:%M:%S')
    write_to_screen_handler.setFormatter(screen_formatter)
    if level:
        write_to_screen_handler.level = level
    logger.addHandler(write_to_screen_handler)


def add_syslog_logging(logger, log_name, settings={}):
    #guessing syslog address
    syslog_address = settings.get('LOGGING_SYSLOG_ADDRESS', None)
    level = settings.get('LOGGING_SYSLOG_LEVEL', None)
    if not syslog_address:
        if sys.platform == 'darwin':
            syslog_address = '/var/run/syslog'
        else:
            syslog_address = '/dev/log'
    syslog_format = settings.get('LOGGING_SYSLOG_FORMAT', log_name+': [%(filename)s:%(funcName)s:%(lineno)d]\t%(levelname)s - %(message).1900s')
    write_to_syslog_handler = logging.handlers.SysLogHandler(address=syslog_address)
    syslog_formatter = logging.Formatter(syslog_format, '%Y-%m-%dT%H:%M:%S')
    write_to_syslog_handler.setFormatter(syslog_formatter)
    if level:
        syslog_formatter.level = level
    logger.addHandler(write_to_syslog_handler)


def add_file_logging(logger, log_name, application_name, settings={}):
    (script_folder, app_name) = code.get_app_name()
    if not application_name:
        application_name = app_name

    log_folder = settings.get('LOGGING_FILE_FOLDER', None)
    if not log_folder:
        log_folder = os.path.join(script_folder, 'log')

    log_folder = log_folder.replace('<app_name>', application_name).replace('<name>', log_name)
    log_folder = os.path.abspath(log_folder)

    if not os.path.isdir(log_folder):
        try:
            os.makedirs(log_folder)
        except:
            print("Warning : permission denied to log in folder '%s'. Will attempt to log in '%s'" %
                  (log_folder, os.path.join(script_folder, 'log')))
            log_folder = os.path.join(script_folder, 'log')

    if not os.path.isdir(log_folder):
        try:
            os.makedirs(log_folder)
        except:
            print("Impossible to log with FILE handler to %s either, abandoning file logging." % log_folder)
            return

    if not os.access(log_folder, os.W_OK):
        print("Warning : permission denied to log in folder '%s'. Will attempt to log in '%s'" %
              (log_folder, os.path.join(script_folder, 'log')))
        log_folder = os.path.join(script_folder, 'log')
        try:
            os.makedirs(log_folder)
        except:
            print("Impossible to log with FILE handler to %s either, abandoning file logging." % log_folder)
            return

    file_format = settings.get('LOGGING_FILE_FORMAT', None)

    log_file = os.path.join(log_folder, log_name + ".txt")

    level = settings.get('LOGGING_FILE_LEVEL', 'DEBUG')

    add_logging_file_handler(logger, log_file, file_format, level=level)


def add_logging_file_handler(logger, log_file, format=None, level=None):
    if not format:
        format = '[%(asctime)s] [%(filename)s:%(funcName)s:%(lineno)d]\t%(levelname)-8s - %(message)s'

    write_to_file_handler = logging.handlers.RotatingFileHandler(log_file, maxBytes=10000000, backupCount=10, encoding='UTF-8')
    file_formatter = logging.Formatter(format, '%Y-%m-%dT%H:%M:%S')
    write_to_file_handler.setFormatter(file_formatter)
    if level:
        write_to_file_handler.level = level
    logger.addHandler(write_to_file_handler)


def add_mongo_logging(logger, log_name, application_name, settings={}):
    (script_folder, app_name) = code.get_app_name()
    if not application_name:
        application_name = app_name

    try:
        import log4mongo.handlers
    except ImportError:
        print("Impossible to log with MONGO handler as log4mongo library is not available.", file=sys.stderr)
        return

    class MyMongoFormatter(log4mongo.handlers.MongoFormatter):
        def format(self, record):
            document = super(MyMongoFormatter, self).format(record)
            del document['threadName']
            del document['thread']
            del document['loggerName']
            del document['module']
            del document['method']
            document['log_name'] = log_name
            document['hostname'] = socket.gethostname()
            return document

    mongo_handler_class = log4mongo.handlers.MongoHandler
    mongo_handler_args = {
        'host': settings.get('LOGGING_MONGO_HOST', "localhost"),
        'port': settings.get('LOGGING_MONGO_PORT', 27017),
        'database_name': settings.get('LOGGING_MONGO_DATABASE', application_name),
        'collection': settings.get('LOGGING_MONGO_COLLECTION', log_name+"_logs"),
        'capped': settings.get('LOGGING_MONGO_CAPPED', True),
        'capped_max': settings.get('LOGGING_MONGO_CAPPED_MAX', 100000),
        'capped_size': settings.get('LOGGING_MONGO_CAPPED_SIZE', 10000000),
        'formatter' : MyMongoFormatter()
    }
    if settings.get('LOGGING_MONGO_BUFFER_SIZE', False):
        mongo_handler_class = log4mongo.handlers.BufferedMongoHandler
        mongo_handler_args.update({
            'buffer_size': settings.get('LOGGING_MONGO_BUFFER_SIZE', 20),
            'buffer_early_flush_level': settings.get('LOGGING_MONGO_BUFFER_FLUSH_LEVEL', logging.CRITICAL),
            'buffer_periodical_flush_timing': settings.get('LOGGING_MONGO_BUFFER_FLUSH_TIMER', 5.0)
        })

    #class MongoFilter(logging.Filter):
    #    def filter(self, record):
    #        record.log_name = log_name
    #        record.hostname = socket.gethostname()
    #        return True
    #
    #logger.addFilter(MongoFilter())

    log4mongo_handler = mongo_handler_class(**mongo_handler_args)

    log4mongo_handler.setLevel(settings.get('LOGGING_MONGO_LEVEL', 'DEBUG'))

    logger.addHandler(log4mongo_handler)

