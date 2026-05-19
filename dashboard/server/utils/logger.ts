type LogLevel = "debug" | "info" | "warn" | "error";

interface LogMeta {
	traceId?: string;
	[key: string]: any;
}

class Logger {
	private meta: LogMeta;
	private isJson: boolean;

	constructor(meta: LogMeta = {}) {
		this.meta = meta;
		// Detect production/JSON preference
		this.isJson = process.env.LOG_FORMAT === "json" || process.env.NODE_ENV === "production";
	}

	child(additionalMeta: LogMeta): Logger {
		return new Logger({ ...this.meta, ...additionalMeta });
	}

	private formatTime(): string {
		return new Date().toISOString();
	}

	private formatLocalTime(): string {
		const d = new Date();
		return d.toTimeString().split(" ")[0] || d.toISOString();
	}

	private log(level: LogLevel, message: string, additionalMeta: LogMeta = {}) {
		const fullMeta = { ...this.meta, ...additionalMeta };
		const traceId = fullMeta.traceId || "no-trace";

		if (this.isJson) {
			const payload = {
				time: this.formatTime(),
				level,
				message,
				...fullMeta,
			};
			console.log(JSON.stringify(payload));
		} else {
			const timeStr = `\x1b[90m[${this.formatLocalTime()}]\x1b[0m`;
			const traceStr = `\x1b[36m[${traceId.slice(0, 13)}]\x1b[0m`;

			let levelStr = "";
			let msgStr = message;

			switch (level) {
				case "debug":
					levelStr = "\x1b[34m[DEBUG]\x1b[0m";
					break;
				case "info":
					levelStr = "\x1b[32m[INFO] \x1b[0m";
					break;
				case "warn":
					levelStr = "\x1b[33m[WARN] \x1b[0m";
					msgStr = `\x1b[33m${message}\x1b[0m`;
					break;
				case "error":
					levelStr = "\x1b[31m[ERROR]\x1b[0m";
					msgStr = `\x1b[31m${message}\x1b[0m`;
					break;
			}

			const cleanMeta = { ...fullMeta };
			delete cleanMeta.traceId;
			const metaStr =
				Object.keys(cleanMeta).length > 0 ? ` \x1b[90m${JSON.stringify(cleanMeta)}\x1b[0m` : "";

			console.log(`${timeStr} ${levelStr} ${traceStr} ${msgStr}${metaStr}`);
		}
	}

	debug(message: string, additionalMeta: LogMeta = {}) {
		this.log("debug", message, additionalMeta);
	}

	info(message: string, additionalMeta: LogMeta = {}) {
		this.log("info", message, additionalMeta);
	}

	warn(message: string, additionalMeta: LogMeta = {}) {
		this.log("warn", message, additionalMeta);
	}

	error(message: string, additionalMeta: LogMeta = {}) {
		this.log("error", message, additionalMeta);
	}
}

export const logger = new Logger();
export type { Logger };
