/** @type {import('next').NextConfig} */
module.exports = {
  reactStrictMode: true,
  env: {
    NEXT_PUBLIC_AGGREGATOR_URL:
      process.env.NEXT_PUBLIC_AGGREGATOR_URL || "http://localhost:8000",
  },
};
