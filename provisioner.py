import os
import stat
import sqlite3
import click
from database import init_db, log_action, DB_NAME

def modify_file_permissions(folder_path, action):
    """Adjusts file permission configurations natively on POSIX/macOS systems."""
    if not os.path.exists(folder_path):
        raise FileNotFoundError(f"Target directory {folder_path} does not exist.")
        
    if action == "grant":
        os.chmod(folder_path, stat.S_IRWXU)  # Owner Read/Write/Execute (0o700)
    elif action == "revoke":
        os.chmod(folder_path, 0o000)        # Complete Lockdown (0o000)

@click.group()
def cli():
    """Legal IAM System: Automated Provisioning & Compliance Logger."""
    init_db()

@cli.command()
@click.option('--operator', required=True, help="Email of administrative executor.")
@click.option('--user', required=True, help="Email of target staff footprint.")
@click.option('--matter', required=True, help="The target Case Matter ID.")
@click.option('--level', type=click.Choice(['READ', 'WRITE', 'ADMIN']), default='READ')
def grant(operator, user, matter, level):
    """Grant restricted access permissions to a specified folder target."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    try:
        cursor.execute("SELECT email FROM users WHERE email=?", (user,))
        if not cursor.fetchone():
            click.secho(f"[-] Error: User {user} not found in system directory.", fg="red")
            return
            
        cursor.execute("SELECT folder_path FROM matters WHERE matter_id=?", (matter,))
        matter_row = cursor.fetchone()
        if not matter_row:
            click.secho(f"[-] Error: Matter {matter} not found.", fg="red")
            return
            
        folder_path = matter_row[0]
        
        cursor.execute("""
            INSERT OR REPLACE INTO access_control (email, matter_id, access_level)
            VALUES (?, ?, ?)
        """, (user, matter, level))
        
        modify_file_permissions(folder_path, "grant")
        
        log_action(cursor, operator, user, matter, "GRANT_ACCESS", "SUCCESS", f"Access level: {level}")
        conn.commit()
        click.secho(f"[+] Success: Access configuration deployed for {user}.", fg="green")
        
    except Exception as e:
        conn.rollback()
        # Create a clean fallback transaction for the failure entry
        fail_conn = sqlite3.connect(DB_NAME)
        fail_cursor = fail_conn.cursor()
        log_action(fail_cursor, operator, user, matter, "GRANT_ACCESS", "FAILED", str(e))
        fail_conn.commit()
        fail_conn.close()
        click.secho(f"[-] Operational Exception Encountered: {str(e)}", fg="red")
    finally:
        conn.close()

@cli.command()
@click.option('--operator', required=True, help="Email of administrative executor.")
@click.option('--user', required=True, help="Email of target staff footprint.")
@click.option('--matter', required=True, help="The target Case Matter ID.")
def revoke(operator, user, matter):
    """Revoke access permission states and apply complete file system isolation."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    try:
        cursor.execute("SELECT folder_path FROM matters WHERE matter_id=?", (matter,))
        matter_row = cursor.fetchone()
        if not matter_row:
            click.secho(f"[-] Error: Matter {matter} not found.", fg="red")
            return
            
        folder_path = matter_row[0]
        
        cursor.execute("DELETE FROM access_control WHERE email=? AND matter_id=?", (user, matter))
        
        modify_file_permissions(folder_path, "revoke")
        
        log_action(cursor, operator, user, matter, "REVOKE_ACCESS", "SUCCESS", "Strict isolation applied.")
        conn.commit()
        click.secho(f"[+] Success: Active permissions stripped from {user}.", fg="green")
        
    except Exception as e:
        conn.rollback()
        fail_conn = sqlite3.connect(DB_NAME)
        fail_cursor = fail_conn.cursor()
        log_action(fail_cursor, operator, user, matter, "REVOKE_ACCESS", "FAILED", str(e))
        fail_conn.commit()
        fail_conn.close()
        click.secho(f"[-] Operational Exception Encountered: {str(e)}", fg="red")
    finally:
        conn.close()

@cli.command()
def logs():
    """Display the formatted chronological compliance history ledger."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT timestamp, operator_email, target_email, matter_id, action, status FROM audit_logs ORDER BY id DESC")
    rows = cursor.fetchall()
    
    if not rows:
        click.echo("No logs present in database.")
        return
        
    click.secho(f"{'Timestamp':<20} | {'Operator':<22} | {'Target User':<22} | {'Matter':<8} | {'Action':<15} | {'Status'}", bold=True)
    click.echo("-" * 105)
    for row in rows:
        color = "green" if row[5] == "SUCCESS" else "red"
        click.secho(f"{row[0]:<20} | {row[1]:<22} | {row[2]:<22} | {row[3]:<8} | {row[4]:<15} | {row[5]}", fg=color)
    conn.close()

if __name__ == "__main__":
    cli()