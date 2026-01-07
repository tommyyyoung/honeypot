import argparse
import sshHoney
import webHoney

if __name__ == "__main__":
    sshHoney.init_db()
    parser = argparse.ArgumentParser(description="Start an SSH honeypot server.")
    parser.add_argument('-a', '--address', type = str, default = '127.0.0.1')
    parser.add_argument('-p', '--port', type = int, default = None)
    parser.add_argument('-u', '--username', type = str, default = 'admin')
    parser.add_argument('-pw', '--password', type = str, default = 'pass')

    parser.add_argument('-s', '--ssh', action = 'store_true')
    parser.add_argument('-w', '--web', action = 'store_true')

    args = parser.parse_args()
    if not args.ssh and not args.web:
        parser.error('No server type specified, add --ssh or --web')

    try:
        if args.ssh:
            args.port = args.port or 2222
            print("Starting SSH honeypot...\r\n")
            sshHoney.runSshHoneypot(args.address, args.port, args.username, args.password)

        if args.web:
            args.port = args.port or 8080
            print("Starting web honeypot...")
            webHoney.runWebHoneypot(port = args.port, inputUsername = args.username, inputPassword = args.password)

    except KeyboardInterrupt:
        print("\nHoneypot server shutting down.")