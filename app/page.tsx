"use client";

import Link from "next/link";
import Image from "next/image";
import { motion } from "framer-motion";
import { MessageSquare, BarChart3, ArrowRight } from "lucide-react";

export default function HomePage(): JSX.Element {
  return (
    <div className="relative flex min-h-[85vh] flex-col items-center justify-center overflow-hidden">
      {/* Background glowing orb - Calm & Cooling */}
      <div className="pointer-events-none absolute left-1/2 top-1/2 -z-10 h-[600px] w-[600px] -translate-x-1/2 -translate-y-1/2 rounded-full bg-blue-100 blur-3xl opacity-60 mix-blend-multiply animate-pulse-slow"></div>

      <motion.div
        initial={{ opacity: 0, y: 40 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.8, ease: "easeOut" }}
        className="z-10 text-center"
      >
        <motion.div
          initial={{ scale: 0.8, opacity: 0 }}
          animate={{ scale: 1, opacity: 1 }}
          transition={{ delay: 0.2, duration: 0.5 }}
          className="mb-6 flex items-center justify-center gap-4"
        >
          <Image
            src="/logo.png"
            alt="DeBias Logo"
            width={72}
            height={72}
            className="shrink-0 drop-shadow-xl"
            priority
          />

          <h1 className="bg-gradient-to-br from-slate-700 to-slate-400 bg-clip-text text-5xl font-extrabold tracking-tight text-transparent sm:text-6xl">
            DeBias
          </h1>
        </motion.div>

        <p className="mx-auto mb-10 max-w-2xl text-lg text-slate-500">
          Bias-mitigated chat interface with live fairness monitoring. Stream responses in real-time while analyzing toxicity, stereotypes, and disparity signals.
        </p>

      </motion.div>

      <motion.div
        initial={{ opacity: 0, y: 40 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.4, duration: 0.8, ease: "easeOut" }}
        className="z-10 grid w-full max-w-4xl grid-cols-1 gap-6 sm:grid-cols-2"
      >
        <Link href="/chat" className="group relative block h-full">
          <div className="absolute -inset-0.5 rounded-3xl bg-gradient-to-r from-sky-300 to-blue-200 opacity-0 blur transition duration-500 group-hover:opacity-50"></div>
          <div className="glass shadow-glass hover:shadow-glass-hover animate-float relative flex h-full flex-col items-start rounded-3xl p-8 transition-all duration-300 group-hover:-translate-y-2">
            <div className="mb-6 rounded-xl bg-sky-100 p-4 text-sky-600">
              <MessageSquare size={28} />
            </div>
            <h2 className="mb-3 text-2xl font-bold text-slate-800">Live Chat</h2>
            <p className="mb-8 text-slate-500">Interact with the bias-mitigated AI in real-time with streaming responses and confidence intervals.</p>
            <div className="mt-auto flex items-center font-semibold text-sky-600 transition-transform group-hover:translate-x-2">
              Start chatting <ArrowRight className="ml-2" size={18} />
            </div>
          </div>
        </Link>

        <Link href="/dashboard" className="group relative block h-full">
          <div className="absolute -inset-0.5 rounded-3xl bg-gradient-to-r from-teal-300 to-cyan-200 opacity-0 blur transition duration-500 group-hover:opacity-50"></div>
          <div className="glass shadow-glass hover:shadow-glass-hover animate-float relative flex h-full flex-col items-start rounded-3xl p-8 transition-all duration-300 group-hover:-translate-y-2" style={{ animationDelay: "0.2s" }}>
            <div className="mb-6 rounded-xl bg-teal-50 p-4 text-teal-600">
              <BarChart3 size={28} />
            </div>
            <h2 className="mb-3 text-2xl font-bold text-slate-800">Fairness Dashboard</h2>
            <p className="mb-8 text-slate-500">Monitor demographic disparities, toxicity scores, and refusal rates across live conversations.</p>
            <div className="mt-auto flex items-center font-semibold text-teal-600 transition-transform group-hover:translate-x-2">
              View metrics <ArrowRight className="ml-2" size={18} />
            </div>
          </div>
        </Link>
      </motion.div>

      <Link
        href="/ppt.html"
        className="fixed bottom-3 right-3 z-50 inline-flex items-center gap-2 rounded-full border border-slate-300/70 bg-white/55 px-3 py-2 text-[11px] font-medium tracking-wide text-slate-500 shadow-sm backdrop-blur-md transition-all duration-300 hover:border-slate-400/80 hover:bg-white/80 hover:text-slate-700 hover:shadow-md md:bottom-4 md:right-4"
        aria-label="Open ppt.html"
      >
        <span className="inline-flex h-5 w-5 items-center justify-center rounded-full bg-sky-100 text-sky-600">
          <ArrowRight size={11} />
        </span>
        <span>ppt.html</span>
      </Link>
    </div>
  );
}
