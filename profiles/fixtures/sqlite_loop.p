function main() -> void : SqliteError {
    db := sqlite_open(":memory:");
    db.exec("CREATE TABLE t(v INTEGER)");
    params := json.parse("[1]");
    for (int i := 0; i < 10000; i++) {
        db.exec("INSERT INTO t(v) VALUES (?)", params);
    }
    rows := db.query("SELECT COUNT(*) AS n FROM t");
    print(json.stringify(rows));
    db.close();
    return;
}
