import 'package:flutter/cupertino.dart';
import 'package:flutter/services.dart';
import 'package:provider/provider.dart';
import 'package:rex_app/application/session_controller.dart';
import 'package:rex_app/core/icons/ios_icon.dart';
import 'package:rex_app/core/theme/app_gradients.dart';
import 'package:rex_app/core/theme/app_palette.dart';
import 'package:rex_app/core/theme/design_tokens.dart';
import 'package:rex_app/core/theme/text_styles.dart';
import 'package:rex_app/core/widgets/brand_mark.dart';
import 'package:rex_app/core/widgets/ios_button.dart';

/// 登录页：主符号 + 产品名 + 表单；背景 brandGradientSoft（海报气质 / 02 §11）。
class LoginPage extends StatefulWidget {
  const LoginPage({super.key});

  @override
  State<LoginPage> createState() => _LoginPageState();
}

class _LoginPageState extends State<LoginPage> {
  final _scroll = ScrollController();
  final _account = TextEditingController();
  final _password = TextEditingController();
  bool _obscure = true;
  bool _remember = true;

  @override
  void dispose() {
    _scroll.dispose();
    _account.dispose();
    _password.dispose();
    super.dispose();
  }

  void _submit() {
    TextInput.finishAutofillContext();
    context.read<SessionController>().demoSignIn();
  }

  @override
  Widget build(BuildContext context) {
    final palette = AppPalette.of(context);
    return CupertinoPageScaffold(
      backgroundColor: palette.mist,
      child: DecoratedBox(
        decoration: BoxDecoration(gradient: AppGradients.soft(context)),
        child: GestureDetector(
          behavior: HitTestBehavior.translucent,
          onTap: () => FocusScope.of(context).unfocus(),
          child: PrimaryScrollController(
            controller: _scroll,
            child: ListView(
              controller: _scroll,
              keyboardDismissBehavior: ScrollViewKeyboardDismissBehavior.onDrag,
              padding: EdgeInsets.fromLTRB(
                AppSpace.space6,
                MediaQuery.paddingOf(context).top + 48,
                AppSpace.space6,
                AppSpace.space8,
              ),
              children: [
                const Center(child: BrandSymbol(size: 64)),
                const SizedBox(height: AppSpace.space4),
                Text(
                  '115REX',
                  style: AppTextStyle.heading1(context),
                  textAlign: TextAlign.center,
                ),
                const SizedBox(height: AppSpace.space2),
                Text(
                  '登录后同步影视库与进度',
                  style: AppTextStyle.caption(context),
                  textAlign: TextAlign.center,
                ),
                const SizedBox(height: AppSpace.space8),
                AutofillGroup(
                  child: Column(
                    children: [
                      _Field(
                        controller: _account,
                        placeholder: '账号',
                        autofillHints: const [AutofillHints.username],
                        textInputAction: TextInputAction.next,
                      ),
                      const SizedBox(height: AppSpace.space3),
                      _Field(
                        controller: _password,
                        placeholder: '密码',
                        obscureText: _obscure,
                        autofillHints: const [AutofillHints.password],
                        textInputAction: TextInputAction.done,
                        onSubmitted: (_) => _submit(),
                        suffix: CupertinoButton(
                          padding: EdgeInsets.zero,
                          minimumSize:
                              const Size(kMinTapTarget, kMinTapTarget),
                          onPressed: () {
                            setState(() => _obscure = !_obscure);
                          },
                          child: IosIconHitTarget(
                            child: IosIcon(
                              _obscure ? IosSf.eye : IosSf.eyeSlash,
                              size: 20,
                              color: palette.textTertiary,
                            ),
                          ),
                        ),
                      ),
                    ],
                  ),
                ),
                const SizedBox(height: AppSpace.space3),
                Row(
                  children: [
                    CupertinoButton(
                      padding: EdgeInsets.zero,
                      minimumSize: const Size(kMinTapTarget, kMinTapTarget),
                      onPressed: () =>
                          setState(() => _remember = !_remember),
                          child: Row(
                        children: [
                          IosIcon(
                            _remember
                                ? IosSf.checkmarkCircleFill
                                : IosSf.circle,
                            size: 22,
                            color: _remember
                                ? palette.primary
                                : palette.textTertiary,
                          ),
                          const SizedBox(width: AppSpace.space2),
                          Text(
                            '记住密码',
                            style: AppTextStyle.caption(context).copyWith(
                              color: palette.textSecondary,
                            ),
                          ),
                        ],
                      ),
                    ),
                    const Spacer(),
                    CupertinoButton(
                      padding: EdgeInsets.zero,
                      onPressed: () {},
                      child: Text(
                        '忘记密码？',
                        style: AppTextStyle.caption(context).copyWith(
                          color: palette.primary,
                        ),
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: AppSpace.space5),
                IosButton(
                  onPressed: _submit,
                  filled: true,
                  child: const Text('登录'),
                ),
                const SizedBox(height: AppSpace.space3),
                Text(
                  '阶段 1：演示登录，点击即进入首页',
                  style: AppTextStyle.caption(context),
                  textAlign: TextAlign.center,
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}

class _Field extends StatelessWidget {
  const _Field({
    required this.controller,
    required this.placeholder,
    required this.autofillHints,
    required this.textInputAction,
    this.obscureText = false,
    this.suffix,
    this.onSubmitted,
  });

  final TextEditingController controller;
  final String placeholder;
  final Iterable<String> autofillHints;
  final TextInputAction textInputAction;
  final bool obscureText;
  final Widget? suffix;
  final ValueChanged<String>? onSubmitted;

  @override
  Widget build(BuildContext context) {
    final palette = AppPalette.of(context);
    return CupertinoTextField(
      controller: controller,
      placeholder: placeholder,
      obscureText: obscureText,
      padding: const EdgeInsets.symmetric(
        horizontal: AppSpace.space4,
        vertical: AppSpace.space4,
      ),
      decoration: BoxDecoration(
        color: palette.surface,
        borderRadius: BorderRadius.circular(AppRadius.radiusLg),
        border: Border.all(color: palette.separator, width: 0.5),
      ),
      autofillHints: autofillHints,
      textInputAction: textInputAction,
      onSubmitted: onSubmitted,
      suffix: suffix,
    );
  }
}
