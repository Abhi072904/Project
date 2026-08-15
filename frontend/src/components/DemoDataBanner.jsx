export default function DemoDataBanner() {
  return (
    <div className="border border-line rounded-lg bg-paper-raised px-5 py-4 mb-8 flex items-center gap-4 flex-wrap">
      <span className="audit-stamp text-stamp shrink-0">Sample data</span>
      <p className="font-body text-sm text-ink-soft max-w-md">
        This is what SubSense looks like once it's had something to work with. Drop in your own
        bank or card statement below and we'll run the same audit — same categories, same leak
        detection — on your real subscriptions.
      </p>
    </div>
  )
}
