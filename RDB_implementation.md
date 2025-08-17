# Redis From Scratch - RDB Persistence Implementation

This project implements a Redis-like server with RDB (Redis Database) persistence functionality from scratch in Python.

## Overview

The Redis server implementation includes a complete RDB persistence mechanism that provides data durability by creating binary snapshots of the in-memory database. This ensures that data can be recovered after server restarts.

## RDB Persistence Mechanism

### What is RDB?

RDB (Redis Database) is a point-in-time snapshot mechanism that serializes the entire dataset to disk in a compact binary format. It provides:

- **Data Durability**: Survives server restarts and crashes
- **Compact Storage**: Binary format with optional compression
- **Fast Recovery**: Quick loading of data on startup
- **Data Integrity**: Checksum validation to detect corruption

### RDB Implementation Architecture

The RDB implementation consists of several key components:

#### 1. RDBHandler (`redis_server/persistence/rdb.py`)

The core component responsible for creating and loading RDB snapshots:

```python
class RDBHandler:
    # Features:
    - Binary serialization with magic header (REDIS0001)
    - GZIP compression (optional)
    - CRC32 checksum verification (optional)
    - Background snapshot creation
    - Thread-safe operations
```

**File Format:**
```
[MAGIC_STRING:5][VERSION:4][COMPRESSED_DATA][CHECKSUM:4]
REDIS0001<compressed_pickle_data><crc32>
```

#### 2. PersistenceConfig (`redis_server/persistence/config.py`)

Configuration management for RDB settings:

```python
# Default RDB Configuration
{
    'rdb_enabled': True,
    'rdb_filename': 'dump.rdb',
    'rdb_compression': True,
    'rdb_checksum': True,
    'rdb_save_conditions': [
        (900, 1),     # Save if 1 key changed in 900 seconds
        (300, 10),    # Save if 10 keys changed in 300 seconds  
        (60, 10000),  # Save if 10000 keys changed in 60 seconds
    ]
}
```

#### 3. PersistenceManager (`redis_server/persistence/manager.py`)

Orchestrates persistence operations:

- Tracks write commands and triggers auto-saves
- Manages background snapshot creation
- Handles periodic persistence tasks
- Coordinates with recovery manager

#### 4. RecoveryManager (`redis_server/persistence/recovery.py`)

Handles data recovery on server startup:

- Validates RDB file integrity
- Loads data from RDB snapshots
- Handles corrupted files gracefully
- Filters expired keys during recovery

### RDB Save Triggers

The RDB system automatically creates snapshots based on configurable conditions:

1. **Automatic Saves**: Based on time + number of changes
   - 1 change in 15 minutes
   - 10 changes in 5 minutes  
   - 10,000 changes in 1 minute

2. **Manual Saves**: Via Redis commands
   - `SAVE`: Synchronous save (blocks server)
   - `BGSAVE`: Background save (non-blocking)

3. **Shutdown Saves**: Automatic save on graceful shutdown

### RDB File Operations

#### Creating Snapshots

1. **Data Collection**: Serialize all keys with values and expiry times
2. **Compression**: Apply GZIP compression (if enabled)
3. **Checksum**: Calculate CRC32 checksum (if enabled)
4. **Atomic Write**: Write to temporary file, then rename
5. **Background Mode**: Use separate thread for non-blocking saves

#### Loading Snapshots

1. **Validation**: Check magic header and version
2. **Decompression**: Decompress GZIP data (if compressed)
3. **Checksum**: Verify data integrity
4. **Deserialization**: Load key-value pairs
5. **Expiry Filtering**: Skip expired keys during load

### Data Store Integration

The RDB system integrates with the main data store (`storage.py`):

- **Write Tracking**: All write commands increment change counter
- **Expiry Handling**: TTL and expiry times are preserved
- **Memory Management**: Efficient serialization of different data types
- **State Consistency**: Thread-safe operations with locking

## Project Structure

```
redis_server/
├── __init__.py
├── server.py              # Main Redis server
├── command.py             # Command handling
├── storage.py             # In-memory data store
├── response.py            # Redis protocol responses
└── persistence/
    ├── __init__.py
    ├── config.py          # Persistence configuration
    ├── manager.py         # Persistence orchestration
    ├── rdb.py            # RDB snapshot implementation
    └── recovery.py        # Data recovery on startup
```

## Manual Testing Guide

### Starting the Server

```bash
# Navigate to project directory
cd Redis_from_scratch

# Start the Redis server
python main.py

# Expected output:
# Recovering data from persistence files...
# No RDB file found, starting with empty database
# Data recovery completed successfully
# RDB enabled: ./data/dump.rdb
# Persistence manager started with RDB enabled: True
# Redis server listening on localhost:6379
```

### Basic RDB Testing

#### 1. Connect to Server

```bash
# Use telnet or nc to connect
telnet localhost 6379
# or
nc localhost 6379
```

#### 2. Set Some Data

```redis
# Set basic key-value pairs
SET key1 "Hello World"
SET key2 "Redis RDB Test"
SET key3 "Persistence Demo"

# Set key with expiration
SETEX temp_key 30 "This will expire"

# Set numeric values
SET counter 42
INCR counter

# Expected responses:
+OK
+OK
+OK
+OK
:43
```

#### 3. Manual RDB Save

```redis
# Synchronous save (blocks until complete)
SAVE

# Expected response:
+OK

# Background save (non-blocking)
BGSAVE

# Expected response:
+Background RDB save started
```

#### 4. Check Save Status

```redis
# Get timestamp of last save
LASTSAVE

# Expected response (Unix timestamp):
:1692211234
```

#### 5. Verify RDB File

```bash
# Check if RDB file was created
ls -la ./data/
# Should see: dump.rdb

# Check file size
du -h ./data/dump.rdb
```

### Persistence Testing

#### 1. Data Persistence Test

```redis
# Set test data
SET persist_test1 "Before restart"
SET persist_test2 "Should survive"
SET counter 100

# Force save
SAVE

# Get current data
GET persist_test1
GET persist_test2
GET counter

# Expected responses:
$13
Before restart
$14
Should survive
$3
100
```

#### 2. Server Restart Test

```bash
# Stop the server (Ctrl+C)
# Restart the server
python main.py

# Expected output should show:
# Loading data from RDB file: ./data/dump.rdb
# Loaded X keys from RDB file
# Data recovery completed successfully
```

#### 3. Verify Data Recovery

```redis
# Connect again and check data
GET persist_test1
GET persist_test2
GET counter

# Expected responses (same as before restart):
$13
Before restart
$14
Should survive
$3
100
```

### Advanced Testing

#### 1. Automatic Save Testing

```redis
# Set many keys to trigger auto-save
SET auto1 "value1"
SET auto2 "value2"
SET auto3 "value3"
SET auto4 "value4"
SET auto5 "value5"
SET auto6 "value6"
SET auto7 "value7"
SET auto8 "value8"
SET auto9 "value9"
SET auto10 "value10"

# Wait and check if auto-save triggered
# Should see console message: "Auto-saving RDB: X changes in Y.Ys"
```

#### 2. Expiry Testing

```redis
# Set keys with expiration
SETEX short_lived 5 "Will expire soon"
SETEX medium_lived 60 "Will expire later"

# Save before expiry
SAVE

# Wait for expiry (>5 seconds)
# Restart server

# Check if expired keys are filtered
GET short_lived    # Should return (nil)
GET medium_lived   # Should return value if not expired
```

#### 3. Large Dataset Testing

```bash
# Use a script to set many keys
for i in {1..1000}; do
    echo "SET bulk_key_$i value_$i" | nc localhost 6379
done

# Force save
echo "SAVE" | nc localhost 6379

# Restart and verify
python main.py
# Should see: "Loaded 1000+ keys from RDB file"
```

### Error Testing

#### 1. Corrupted RDB File

```bash
# Corrupt the RDB file
echo "corrupted" > ./data/dump.rdb

# Restart server
python main.py

# Expected output:
# RDB file corruption detected: ...
# Starting with empty database. Consider restoring from backup.
```

#### 2. Missing RDB File

```bash
# Remove RDB file
rm ./data/dump.rdb

# Restart server
python main.py

# Expected output:
# No RDB file found, starting with empty database
```

### Performance Testing

#### 1. Save Performance

```redis
# Time synchronous save
TIME SAVE

# Time background save
TIME BGSAVE
```

#### 2. Recovery Performance

```bash
# Measure startup time with large dataset
time python main.py
```

## Configuration

### Custom RDB Configuration

```python
# Custom persistence config
config = {
    'rdb_enabled': True,
    'rdb_filename': 'custom.rdb',
    'rdb_compression': True,
    'rdb_checksum': True,
    'rdb_save_conditions': [
        (60, 1),      # More frequent saves
        (30, 100),    # Save every 30s if 100 changes
    ],
    'data_dir': './custom_data'
}

# Start server with custom config
from redis_server import RedisServer
server = RedisServer(persistence_config=config)
server.start()
```

### Environment Variables

```bash
# Set custom data directory
export REDIS_DATA_DIR="/var/lib/redis"

# Disable compression
export REDIS_RDB_COMPRESSION="false"

# Custom RDB filename
export REDIS_RDB_FILENAME="backup.rdb"
```

## Troubleshooting

### Common Issues

1. **Permission Errors**
   ```bash
   # Ensure data directory is writable
   chmod 755 ./data
   ```

2. **Disk Space**
   ```bash
   # Check available space
   df -h ./data
   ```

3. **File Locks**
   ```bash
   # Check for processes using RDB file
   lsof ./data/dump.rdb
   ```

### Debug Information

```redis
# Check persistence status
CONFIG GET save
CONFIG GET dir
CONFIG GET dbfilename

# Debug information
DEBUG OBJECT key1
```

## Implementation Notes

### Thread Safety

- All RDB operations use thread locks
- Background saves don't block main server thread
- Atomic file operations prevent corruption

### Memory Usage

- RDB snapshots require temporary memory equal to dataset size
- Compression reduces disk usage by ~30-50%
- Background saves use copy-on-write semantics where possible

### Recovery Guarantees

- Last consistent snapshot is always recovered
- Corrupted files are handled gracefully
- No partial state recovery (all-or-nothing)

### Performance Characteristics

- **Save Time**: O(n) where n is number of keys
- **Recovery Time**: O(n) where n is number of keys
- **File Size**: Compressed binary format, ~50% smaller than AOF
- **Memory Overhead**: Minimal during normal operations

## Future Enhancements

1. **RDB Format Versioning**: Support multiple RDB format versions
2. **Incremental Snapshots**: Delta compression between snapshots  
3. **Encrypted RDB**: Add encryption support for sensitive data
4. **Cloud Storage**: Direct save/load from cloud storage
5. **Compression Algorithms**: Support for different compression methods