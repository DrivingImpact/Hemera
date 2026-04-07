import { SignIn } from "@clerk/nextjs";

export default function SignInPage() {
  return (
    <div className="min-h-screen bg-paper flex flex-col items-center justify-center gap-6">
      <div className="text-center">
        <div className="text-teal text-[11px] font-bold uppercase tracking-[4px]">Hemera</div>
        <p className="text-muted text-sm mt-1">Supply Chain Carbon Intelligence</p>
      </div>
      <SignIn />
    </div>
  );
}
